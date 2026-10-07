/**
 * Webhook Handlers & Payload Normalizers (n8n & Node.js)
 * Permet de parser et unifier les flux entrants :
 * - Webhooks WhatsApp (WATI, Zoko, WhatHub, Meta Cloud API)
 * - Webhooks Paiements (Systeme.io, Stripe, PayTech)
 * Auteur : Agent IA Commercial
 */

/**
 * Normalise les payloads WhatsApp reçus selon les différents fournisseurs
 */
function parseWhatsAppWebhook(body) {
  let senderPhone = "";
  let messageText = "";
  let messageId = "";
  let senderName = "Prospect";
  let timestamp = new Date().toISOString();

  // 1. Format Meta WhatsApp Cloud API officiel
  if (body.object === "whatsapp_business_account" && body.entry) {
    const changes = body.entry[0]?.changes[0]?.value;
    const message = changes?.messages?.[0];
    const contact = changes?.contacts?.[0];

    if (message) {
      senderPhone = "+" + message.from;
      messageText = message.text?.body || message.button?.text || "";
      messageId = message.id;
      senderName = contact?.profile?.name || "Prospect";
    }
  }
  // 2. Format WATI
  else if (body.waId || body.senderPhone) {
    senderPhone = body.waId ? (body.waId.startsWith("+") ? body.waId : "+" + body.waId) : body.senderPhone;
    messageText = body.text || body.messageText || "";
    messageId = body.id || `wati_${Date.now()}`;
    senderName = body.senderName || body.name || "Prospect";
  }
  // 3. Format Zoko
  else if (body.platform && body.customer) {
    senderPhone = body.customer.phone || body.recipient;
    messageText = body.text || "";
    messageId = body.id || `zoko_${Date.now()}`;
    senderName = body.customer.name || "Prospect";
  }
  // 4. Format générique / WhatHub
  else {
    senderPhone = body.phone || body.from || body.mobile || "";
    messageText = body.message || body.body || body.content || "";
    messageId = body.msg_id || `gen_${Date.now()}`;
    senderName = body.name || body.user_name || "Prospect";
  }

  // Nettoyage du numéro au format E.164
  senderPhone = senderPhone.replace(/[^\d+]/g, "");
  if (!senderPhone.startsWith("+") && senderPhone.length > 0) {
    senderPhone = "+" + senderPhone;
  }

  return {
    provider: "whatsapp",
    sender_phone: senderPhone,
    sender_name: senderName,
    message_text: messageText.trim(),
    message_id: messageId,
    received_at: timestamp
  };
}

/**
 * Normalise les webhooks de paiements (Systeme.io, Stripe, PayTech)
 */
function parsePaymentWebhook(body) {
  let customerEmail = "";
  let customerPhone = "";
  let customerName = "";
  let productName = "Pack Formations Digitales";
  let amountPaid = 0;
  let currency = "XOF";
  let paymentStatus = "SUCCESS";
  let transactionId = "";

  // 1. Format Systeme.io
  if (body.type === "contact.enrolled_in_course" || body.type === "sale.completed" || body.contact) {
    customerEmail = body.contact?.email || body.email || "";
    customerName = `${body.contact?.first_name || ""} ${body.contact?.surname || ""}`.trim();
    customerPhone = body.contact?.fields?.phone || body.contact?.fields?.whatsapp || body.phone || "";
    productName = body.course?.name || body.order?.product_name || "Pack Formations Digitales";
    amountPaid = body.order?.amount || 0;
    transactionId = body.order?.id || `sio_${Date.now()}`;
  }
  // 2. Format Stripe
  else if (body.object === "event" && body.type && body.type.startsWith("checkout.session")) {
    const session = body.data?.object || {};
    customerEmail = session.customer_details?.email || "";
    customerName = session.customer_details?.name || "";
    customerPhone = session.customer_details?.phone || "";
    amountPaid = (session.amount_total || 0) / 100;
    currency = session.currency?.toUpperCase() || "EUR";
    transactionId = session.id;
    productName = session.metadata?.product_name || "Pack Formations Digitales";
  }
  // 3. Format PayTech (Mobile Money Afrique)
  else if (body.type_event === "sale_complete" || body.item_price) {
    customerEmail = body.custom_field?.email || body.client_email || "";
    customerPhone = body.custom_field?.phone || body.client_phone || "";
    customerName = body.custom_field?.name || body.client_name || "";
    amountPaid = parseFloat(body.item_price || 0);
    currency = body.currency || "XOF";
    transactionId = body.token || body.ref_command || `paytech_${Date.now()}`;
  }

  // Nettoyage téléphone
  customerPhone = customerPhone.replace(/[^\d+]/g, "");
  if (customerPhone && !customerPhone.startsWith("+")) {
    customerPhone = "+" + customerPhone;
  }

  return {
    event_type: "PAYMENT_CONFIRMED",
    customer_email: customerEmail,
    customer_name: customerName || "Nouveau Client",
    customer_phone: customerPhone,
    product_name: productName,
    amount_paid: amountPaid,
    currency: currency,
    transaction_id: transactionId,
    payment_status: paymentStatus,
    timestamp: new Date().toISOString()
  };
}

module.exports = {
  parseWhatsAppWebhook,
  parsePaymentWebhook
};
