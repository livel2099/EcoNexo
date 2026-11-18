"""Durable email/WhatsApp dispatch. Provider acceptance is not proof of delivery."""
import asyncio
import json
import re
import smtplib
import ssl
from email.message import EmailMessage
import httpx
from . import db
from .config import get_settings

def readiness():
    s=get_settings()
    return {'email':bool(s.brazil_smtp_host and s.brazil_smtp_user and s.brazil_smtp_password and s.brazil_mail_from),
            'whatsapp':bool(s.brazil_whatsapp_token and re.fullmatch(r'\d+',s.brazil_whatsapp_phone_id) and s.brazil_whatsapp_template and re.fullmatch(r'v\d+\.\d+',s.brazil_whatsapp_version)),
            'scheduler':s.brazil_operations_enabled}

async def enqueue(conn, org_id, alert_ids):
    if not alert_ids: return
    await conn.execute("""INSERT INTO brazil_delivery_queue(org_id,alert_id,channel,recipient)
        SELECT a.org_id,a.id,r->>'channel',r->>'address'
        FROM brazil_operations_alerts a JOIN brazil_operations_settings s ON s.org_id=a.org_id
        CROSS JOIN LATERAL jsonb_array_elements(s.recipients) r
        WHERE a.org_id=$1 AND a.id=ANY($2::uuid[]) AND s.enabled AND (r->>'consent')::boolean
        ON CONFLICT(alert_id,channel,recipient) DO NOTHING""",org_id,alert_ids)

def mail(to, subject, body, delivery_id):
    s=get_settings()
    message=EmailMessage();message['From']=s.brazil_mail_from;message['To']=to
    message['Subject']=subject;message['Message-ID']=f'<econexo-{delivery_id}@{s.brazil_mail_from.split("@")[-1]}>'
    message.set_content(body)
    with smtplib.SMTP(s.brazil_smtp_host,s.brazil_smtp_port,timeout=20) as client:
        client.starttls(context=ssl.create_default_context())
        client.login(s.brazil_smtp_user,s.brazil_smtp_password)
        refused=client.send_message(message)
        if refused: raise smtplib.SMTPRecipientsRefused(refused)
    return str(message['Message-ID'])

async def send(row):
    s=get_settings()
    kind={'fire':'Foco de calor por verificar','pest':'Ocorrência fitossanitária','vegetation':'Anomalia de vegetação'}[row['kind']]
    body=f"Econexo Brasil: {kind}. Talhão: {row['name']} ({row['code']}). Prioridade: {row['priority']}. Observação: {row['observed_at'].isoformat()}. Alerta: {row['alert_id']}. Verifique a evidência e coordene a equipe no painel."
    if row['channel']=='email': return await asyncio.to_thread(mail,row['recipient'],'Econexo Brasil: '+kind,body,row['id'])
    async with httpx.AsyncClient(timeout=20) as client:
        response=await client.post(f'https://graph.facebook.com/{s.brazil_whatsapp_version}/{s.brazil_whatsapp_phone_id}/messages',
            headers={'Authorization':'Bearer '+s.brazil_whatsapp_token},json={'messaging_product':'whatsapp','to':row['recipient'].lstrip('+'),'type':'template',
            'template':{'name':s.brazil_whatsapp_template,'language':{'code':'pt_BR'},'components':[{'type':'body','parameters':[{'type':'text','text':body}]}]}})
        response.raise_for_status()
        return response.json()['messages'][0]['id']

async def dispatch_batch():
    ready=readiness()
    # A process can die after sending. Never automatically duplicate an ambiguous send.
    await db.pool().execute("""UPDATE brazil_delivery_queue SET status='uncertain',last_error='worker_interrupted'
        WHERE status='processing' AND claimed_at<now()-interval '5 minutes'""")
    for _ in range(20):
        async with db.pool().acquire() as conn:
            async with conn.transaction():
                row=await conn.fetchrow("""SELECT q.*,a.kind,a.priority,a.observed_at,p.name,p.code,s.recipients,s.enabled
                    FROM brazil_delivery_queue q JOIN brazil_operations_alerts a ON a.id=q.alert_id AND a.org_id=q.org_id
                    JOIN brazil_parcels p ON p.id=a.parcel_id AND p.org_id=a.org_id
                    JOIN brazil_operations_settings s ON s.org_id=q.org_id
                    JOIN organizations o ON o.id=q.org_id
                    JOIN organization_subscriptions sub ON sub.org_id=q.org_id
                    WHERE q.status='pending' AND q.available_at<=now()
                    AND o.is_active AND o.access_status='approved' AND sub.status IN ('active','trial')
                    AND (sub.expires_at IS NULL OR sub.expires_at>now())
                    AND ((q.channel='email' AND $1) OR (q.channel='whatsapp' AND $2))
                    ORDER BY q.available_at LIMIT 1 FOR UPDATE OF q SKIP LOCKED""",ready['email'],ready['whatsapp'])
                if row is None: return
                recipients=json.loads(row['recipients']) if isinstance(row['recipients'],str) else row['recipients']
                authorized=row['enabled'] and any(r['channel']==row['channel'] and r['address']==row['recipient'] and r.get('consent') for r in recipients)
                if not authorized:
                    await conn.execute("UPDATE brazil_delivery_queue SET status='cancelled' WHERE id=$1",row['id']);continue
                await conn.execute("UPDATE brazil_delivery_queue SET status='processing',claimed_at=now(),attempts=attempts+1 WHERE id=$1",row['id'])
        status='accepted';provider_id=None;error=None
        try: provider_id=await send(row)
        except httpx.HTTPStatusError as exc:
            # Provider rejected the request: retry throttling/server rejection, bounded.
            status='pending' if (exc.response.status_code==429 or exc.response.status_code>=500) and row['attempts']<5 else 'failed'
            error=f'provider_http_{exc.response.status_code}'
        except (smtplib.SMTPAuthenticationError,smtplib.SMTPRecipientsRefused): status='failed';error='smtp_rejected'
        except Exception: status='uncertain';error='provider_result_unknown'
        await db.pool().execute("""UPDATE brazil_delivery_queue SET status=$2,provider_id=$3,last_error=$4,
            available_at=now()+interval '10 minutes' WHERE id=$1""",row['id'],status,provider_id,error)
