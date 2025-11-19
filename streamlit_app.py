import pdfkit
import streamlit as st
import requests
import json
from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime, date

st.set_page_config(layout="centered", page_icon="💰", page_title="Invoice Generator - The ATM Agency")
st.title("💰 The ATM Agency - Invoice Generator")

st.write(
    "Generate professional invoices and send them directly to your n8n workflow for automated processing."
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
        help="Enter your n8n webhook URL to send invoice data"
    )
    send_to_webhook = st.checkbox("Send to n8n webhook", value=True)
    generate_pdf = st.checkbox("Generate PDF", value=True)
    
    st.divider()
    st.caption("📌 The webhook will receive invoice data in JSON format")

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
    
    product_type = left.selectbox(
        "Product/Service Type*",
        ["Digital Marketing Services", "Social Media Management", "SEO Optimization", 
         "Content Creation", "Brand Strategy", "Web Development", "Consulting Services"]
    )
    quantity = right.number_input("Quantity*", min_value=1, max_value=1000, value=1)
    
    price_per_unit = st.slider("Price per Unit ($)*", min_value=1, max_value=10000, value=500, step=50)
    
    # Calculate total
    tax_rate = st.slider("Tax Rate (%)", min_value=0.0, max_value=20.0, value=0.0, step=0.5)
    
    subtotal = price_per_unit * quantity
    tax_amount = subtotal * (tax_rate / 100)
    total = subtotal + tax_amount
    
    # Display calculation
    st.info(f"**Subtotal:** ${subtotal:,.2f} | **Tax ({tax_rate}%):** ${tax_amount:,.2f} | **Total:** ${total:,.2f}")
    
    notes = st.text_area("Additional Notes", placeholder="Enter any special instructions or notes...")
    
    st.divider()
    submit = st.form_submit_button("🚀 Generate Invoice", use_container_width=True)

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
        
        # Send to n8n webhook
        webhook_success = False
        if send_to_webhook and webhook_url:
            try:
                with st.spinner("📤 Sending to n8n webhook..."):
                    response = requests.post(
                        webhook_url,
                        json=invoice_data,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                    
                    if response.status_code in [200, 201, 202]:
                        st.success(f"✅ Successfully sent to n8n webhook! (Status: {response.status_code})")
                        webhook_success = True
                        
                        # Show response if available
                        with st.expander("📋 View Webhook Response"):
                            st.json(response.json() if response.text else {"status": "success"})
                    else:
                        st.error(f"❌ Webhook request failed with status {response.status_code}")
                        st.code(response.text)
            except requests.exceptions.Timeout:
                st.error("⏱️ Webhook request timed out. Please check your n8n instance.")
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Error sending to webhook: {str(e)}")
        
        # Generate PDF if requested
        if generate_pdf:
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
                        product_type=product_type,
                        quantity=quantity,
                        price_per_unit=f"{price_per_unit:,.2f}",
                        subtotal=f"{subtotal:,.2f}",
                        tax_rate=f"{tax_rate}",
                        tax_amount=f"{tax_amount:,.2f}",
                        total=f"{total:,.2f}",
                        notes=notes
                    )
                    
                    pdf = pdfkit.from_string(html, False)
                    st.balloons()
                    
                    st.success("🎉 Your invoice was generated successfully!")
                    
                    # Download button
                    st.download_button(
                        "⬇️ Download Invoice PDF",
                        data=pdf,
                        file_name=f"invoice_{invoice_number}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            except Exception as e:
                st.error(f"❌ Error generating PDF: {str(e)}")
                st.info("💡 Make sure wkhtmltopdf is installed on your system")
        
        # Show JSON data preview
        with st.expander("🔍 View Invoice Data (JSON)"):
            st.json(invoice_data)
        
        # Copy to clipboard option
        st.code(json.dumps(invoice_data, indent=2), language="json")

# Footer
st.divider()
st.caption("Made with ❤️ by The ATM Agency | Powered by Streamlit")
