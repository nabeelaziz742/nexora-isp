# WhatsApp Templates (Meta Cloud API)

Meta only delivers **business-initiated** WhatsApp messages (bills, reminders,
receipts, suspension notices) through **approved message templates**. Plain
text is delivered only to customers who messaged the ISP in the last 24 hours.

Nexora sends a template automatically when the communication template has a
Meta template name. New tenants get the names below pre-filled, so the ISP
only has to create these templates in Meta.

## 1. Create the templates in Meta

Meta Business Manager -> WhatsApp Manager -> Message templates -> Create.

For every template:

- **Category:** Utility
- **Language:** English (`en`). If you choose another language, put its code
  (for example `ur` or `en_US`) in the template's *Language Code* in Nexora.
- **Name:** exactly as below (lowercase, underscores).
- **Body:** copy the text below. Keep the `{{1}}`, `{{2}}` placeholders in the
  same order; Meta asks for a sample value for each one.

| Template name | Used for | Body text | Variables in order |
|---|---|---|---|
| `nexora_invoice_generated` | New invoice | Dear {{1}}, your internet bill {{2}} of PKR {{3}} has been generated. Please pay by {{4}}. Thank you. | customer_name, invoice_number, total_amount, due_date |
| `nexora_bill_due_reminder` | Due reminder | Dear {{1}}, a reminder that PKR {{2}} for bill {{3}} is due on {{4}}. | customer_name, outstanding_amount, invoice_number, due_date |
| `nexora_bill_overdue` | Overdue reminder | Dear {{1}}, your internet bill of PKR {{2}} (bill {{3}}) was due on {{4}} and is now overdue. Please pay to avoid service interruption. | customer_name, outstanding_amount, invoice_number, due_date |
| `nexora_suspension_warning` | Final warning before suspension | Dear {{1}}, your internet service {{2}} will be suspended on {{3}} due to an outstanding balance of PKR {{4}}. | customer_name, service_number, suspension_date, outstanding_amount |
| `nexora_service_suspended` | Service suspended | Dear {{1}}, your internet service {{2}} has been suspended due to unpaid dues of PKR {{3}}. | customer_name, service_number, outstanding_amount |
| `nexora_service_restored` | Service restored | Dear {{1}}, your internet service {{2}} has been restored. Thank you for your payment. | customer_name, service_number |
| `nexora_payment_received` | Payment receipt | Dear {{1}}, we received your payment of PKR {{2}} (receipt {{3}}). Remaining balance: PKR {{4}}. | customer_name, paid_amount, payment_number, outstanding_amount |
| `nexora_promise_to_pay` | Promise to pay recorded | Dear {{1}}, your promise to pay PKR {{2}} by {{3}} has been recorded. | customer_name, promised_amount, deadline |
| `nexora_complaint_received` | Support ticket received | Dear {{1}}, your complaint {{2}} has been received. Our team will contact you soon. | customer_name, complaint_number |

You may change the wording, as long as the number and order of the
placeholders stay the same. If you change the order, update *Template
Variables* in Nexora to match.

## 2. Connect WhatsApp in Nexora

Communications -> Providers -> WhatsApp: enter the Phone Number ID and access
token from Meta and run the health check until it shows **Connected**.
Messages are never sent to Meta while the provider is not connected.

## 3. Check or change a template in Nexora

Communications -> Templates -> open a WhatsApp template. The
**WhatsApp (Meta) Template** section holds:

- **Approved Template Name** - must match Meta exactly.
- **Language Code** - must match the language approved in Meta.
- **Template Variables (in order)** - comma-separated; the first fills `{{1}}`.

Leave the name empty to send the message body as plain text (24-hour window
only).

## 4. Troubleshooting

Failed messages show the Meta error in Communications -> Logs (and on the
notification job). Common ones:

| Meta error | Meaning | Fix |
|---|---|---|
| 132001 Template name does not exist in the translation | Name or language does not match an approved template | Check the name and language code |
| 132000 Number of parameters does not match | Variable count differs from the template | Fix *Template Variables* |
| 131047 Re-engagement message | Plain text sent outside the 24-hour window | Add an approved template name |
| 131026 Message undeliverable | Number is not on WhatsApp | Check the customer's phone number |
