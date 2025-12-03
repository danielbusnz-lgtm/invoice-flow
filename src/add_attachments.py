from attachments import fetch_messages_with_attachments
from datetime import datetime
from quickbooks.objects.attachable import Attachable
from quickbooks.objects.base import AttachableRef
from pathlib import Path
from push_invoice import QuickbooksInvoiceService

def upload_file(attachments):
    project_root = Path(__file__).parent.parent
    attachment_dir= project_root / "attachments"
    
    file_path = attachment_dir/ filename

    attachable=Attachable()
    attachable.FileName=filename
    attachable._FilePath= str(file_path)
    attachable_ref=AttachableRef()
    attachable_ref.EntityRef=invoice_ref
    attachable.AttachableRef.append(attachable_ref)
    attachable.save(qb=qb_client) 


