import sys                                                                                                                                                                 
from pathlib import Path                                                                                                                                                    
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))                                                                                                                      
from services.quickbooks_service import QuickbooksInvoiceService  
try:
    qb =  QuickbooksInvoiceService()
except:
    return 

context = qb.get_customers_context()

match = qb.match_category_to_account('account')

match

address = qb.find_customer_by_address("24 courier drive")
address 




#print(context)
