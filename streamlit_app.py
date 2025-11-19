import pdfkit
import streamlit as st
import requests
import json
from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime, date
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
import base64

st.set_page_config(layout="centered", page_icon="💰", page_title="Invoice Generator - The ATM Agency")
st.title("💰 The ATM Agency - Invoice Generator")

st.write(
    "Generate professional invoices and automatically send to n8n and Google Drive."
)

# Initialize Jinja2 environment
env = Environment(loader=FileSystemLoader("."), autoescape=select_autoescape())
template = env.get_template("invoice_template.html")

# Webhook configuration in sidebar
with st.sidebar:
    st.header("⚙️ Webhook Settings")
    webhook_url = st.text_input(
        "n8n Webhook URL",
        placeholder="https://your-n8n-instance.com/webhook/invoice",
        help="Enter your n8n webhook URL to send invoice data and PDF"
    )
    
    st.divider()
    st.header("☁️ Google Drive Settings")
    
    # Upload Google service account JSON
    uploaded_service_file = st.file_uploader(
        "Upload Service Account JSON",
        type=["json"],
        help="Upload your Google Cloud service account JSON file for Drive access"
    )
    
    gdrive_folder_id = st.text_input(
        "Google Drive Folder ID",
        placeholder="1ABC123xyz...",
        help="Enter the Google Drive folder ID where PDFs will be uploaded"
    )
    
    # Store credentials in session state
    if uploaded_service_file is not None:
        try:
            service_account_info = json.load(uploaded_service_file)
            st.session_state['gdrive_credentials'] = service_account_info
            st.success("✅ Service account file loaded!")
        except Exception as e:
            st.error(f"❌ Error loading service account: {str(e)}")
    
    st.divider()
    st.caption("📌 PDFs will be auto-sent to n8n webhook and Google Drive")

# Main invoice form
with st.form("invoice_form"):
    st.subheader("🏢 Company Information")
    
    col1, col2 = st.columns((1, 10))
    color = col1.color_picker("Brand Color", value="#FF6B35")
    company_name = col2.text_input("Company Name", value="The ATM Agency")
    
    st.divider()
    st.subheader("👤 Customer Information")
    
    left, right = st.columns(2)
    customer_name = left.text_input("Customer Name*", placeholder="John Doe")
    customer_email = right.text_input("Customer Email", placeholder="customer@example.com")
    customer_address = left.text_input("Customer Address*", placeholder="123 Main St, City, State")
    customer_phone = right.text_input("Customer Phone", placeholder="+1 (555) 123-4567")
    
    st.divider()
    st.subheader("📦 Invoice Details")
    
    left, right = st.columns(2)
    invoice_number = left.text_input("Invoice Number", value=f"INV-{datetime.now().strftime('%Y%m%d-%H%M')}")
    invoice_date = right.date_input("Invoice Date", value=date.today())
    
    sales_agent = st.text_input("Sales Agent Name", placeholder="Enter agent name", value="")
    
    product_type = left.selectbox(
        "Product/Service Type*",
        ["Digital Marketing Services", "Social Media Management", "SEO Optimization", 
         "Content Creation", "Brand Strategy", "Web Development", "Consulting Services"]
    )
    quantity = right.number_input("Quantity*", min_value=1, max_value=1000, value=1)
    
    price_per_unit = st.number_input(
        "Price per Unit ($)*", 
        min_value=0.01, 
        max_value=1000000.00, 
        value=500.00, 
        step=50.00,
        format="%.2f"
    )
    
    # Calculate total
    tax_rate = st.slider("Tax Rate (%)", min_value=0.0, max_value=20.0, value=0.0, step=0.5)
    
    subtotal = price_per_unit * quantity
    tax_amount = subtotal * (tax_rate / 100)
    total = subtotal + tax_amount
    
    # Display calculation
    st.info(f"**Subtotal:** ${subtotal:,.2f} | **Tax ({tax_rate}%):** ${tax_amount:,.2f} | **Total:** ${total:,.2f}")
    
    notes = st.text_area("Additional Notes", placeholder="Enter any special instructions or notes...")
    
    st.divider()
    submit = st.form_submit_button("🚀 Generate & Send Invoice", use_container_width=True)

# Process form submission
if submit:
    # Validate required fields
    if not customer_name or not customer_address:
        st.error("⚠️ Please fill in all required fields marked with *")
    else:
        # Prepare invoice data for webhook
        invoice_data = {
            "invoice_number": invoice_number,
            "invoice_date": invoice_date.strftime("%Y-%m-%d"),
            "sales_agent": sales_agent if sales_agent else "N/A",
            "company": {
                "name": company_name,
                "address": "4218 Blackwell Street, Anchorage, Alaska",
                "phone": "907-334-3873",
                "color": color
            },
            "customer": {
                "name": customer_name,
                "email": customer_email,
                "address": customer_address,
                "phone": customer_phone
            },
            "items": [
                {
                    "product_type": product_type,
                    "quantity": quantity,
                    "price_per_unit": price_per_unit,
                    "subtotal": subtotal
                }
            ],
            "financial": {
                "subtotal": subtotal,
                "tax_rate": tax_rate,
                "tax_amount": tax_amount,
                "total": total,
                "currency": "USD"
            },
            "notes": notes,
            "generated_at": datetime.now().isoformat()
        }
        
        # Generate PDF
        pdf_bytes = None
        try:
            with st.spinner("📄 Generating PDF..."):
                html = template.render(
                    color=color,
                    company_name=company_name,
                    invoice_number=invoice_number,
                    invoice_date=invoice_date.strftime("%B %d, %Y"),
                    customer_name=customer_name,
                    customer_address=customer_address,
                    customer_email=customer_email,
                    customer_phone=customer_phone,
                    sales_agent=sales_agent if sales_agent else "N/A",
                    product_type=product_type,
                    quantity=quantity,
                    price_per_unit=f"{price_per_unit:,.2f}",
                    subtotal=f"{subtotal:,.2f}",
                    tax_rate=f"{tax_rate}",
                    tax_amount=f"{tax_amount:,.2f}",
                    total=f"{total:,.2f}",
                    notes=notes
                )
                
                pdf_bytes = pdfkit.from_string(html, False)
                st.success("✅ PDF generated successfully!")
        except Exception as e:
            st.error(f"❌ Error generating PDF: {str(e)}")
            st.info("💡 Make sure wkhtmltopdf is installed on your system")
        
        if webhook_url and pdf_bytes:
            try:
                with st.spinner("📤 Sending to n8n webhook..."):
                    # Encode PDF to base64 for transmission
                    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
                    
                    # Add PDF data to payload
                    webhook_payload = {
                        **invoice_data,
                        "pdf": {
                            "filename": f"invoice_{invoice_number}.pdf",
                            "data": pdf_base64,
                            "mime_type": "application/pdf"
                        }
                    }
                    
                    response = requests.post(
                        webhook_url,
                        json=webhook_payload,
                        headers={"Content-Type": "application/json"},
                        timeout=30
                    )
                    
                    if response.status_code in [200, 201, 202]:
                        st.success(f"✅ Successfully sent to n8n webhook! (Status: {response.status_code})")
                        
                        # Show response if available
                        with st.expander("📋 View Webhook Response"):
                            try:
                                st.json(response.json() if response.text else {"status": "success"})
                            except:
                                st.text(response.text)
                    else:
                        st.error(f"❌ Webhook request failed with status {response.status_code}")
                        st.code(response.text)
            except requests.exceptions.Timeout:
                st.error("⏱️ Webhook request timed out. Please check your n8n instance.")
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Error sending to webhook: {str(e)}")
        
        if pdf_bytes and 'gdrive_credentials' in st.session_state and gdrive_folder_id:
            try:
                with st.spinner("☁️ Uploading to Google Drive..."):
                    # Create credentials from service account info
                    credentials = service_account.Credentials.from_service_account_info(
                        st.session_state['gdrive_credentials'],
                        scopes=['https://www.googleapis.com/auth/drive.file']
                    )
                    
                    # Build Drive service
                    service = build('drive', 'v3', credentials=credentials)
                    
                    # File metadata
                    file_metadata = {
                        'name': f'invoice_{invoice_number}.pdf',
                        'parents': [gdrive_folder_id]
                    }
                    
                    # Upload file
                    media = MediaInMemoryUpload(
                        pdf_bytes,
                        mimetype='application/pdf',
                        resumable=True
                    )
                    
                    file = service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id, webViewLink'
                    ).execute()
                    
                    st.success(f"✅ Uploaded to Google Drive! File ID: {file.get('id')}")
                    st.info(f"🔗 [View in Drive]({file.get('webViewLink')})")
                    
            except Exception as e:
                st.error(f"❌ Error uploading to Google Drive: {str(e)}")
                st.info("💡 Make sure the service account has access to the folder")
        
        # Show success and download option
        if pdf_bytes:
            st.balloons()
            
            # Download button
            st.download_button(
                "⬇️ Download Invoice PDF",
                data=pdf_bytes,
                file_name=f"invoice_{invoice_number}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        
        # Show JSON data preview
        with st.expander("🔍 View Invoice Data (JSON)"):
            # Don't show the base64 PDF in the preview as it's too long
            preview_data = {k: v for k, v in invoice_data.items()}
            st.json(preview_data)

# Footer
st.divider()
st.caption("Made with ❤️ by The ATM Agency | Powered by Streamlit")

