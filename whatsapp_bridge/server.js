const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const pino = require('pino');
const express = require('express');
const qrcode = require('qrcode');
const http = require('http');
const path = require('path');
const fs = require('fs');

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3001;
const AI_WEBHOOK_URL = process.env.AI_WEBHOOK_URL || 'https://commercial-ia-autonome.onrender.com/webhook/whatsapp';
const AUTH_DIR = path.join(__dirname, 'auth_info_baileys');

let sock = null;
let currentQrCodeDataUrl = null;
let connectionStatus = 'DISCONNECTED'; // DISCONNECTED, SCAN_QR, CONNECTED
let connectedNumber = null;

async function startWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
    const { version } = await fetchLatestBaileysVersion();

    sock = makeWASocket({
        version,
        logger: pino({ level: 'silent' }),
        printQRInTerminal: true,
        auth: state,
        browser: ['Commercial IA Autonome', 'Chrome', '120.0.0']
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            connectionStatus = 'SCAN_QR';
            try {
                currentQrCodeDataUrl = await qrcode.toDataURL(qr);
                console.log('⚡ [WhatsApp Bridge] Nouveau QR Code généré et prêt à être scanné.');
            } catch (err) {
                console.error('Erreur génération QR DataURL:', err);
            }
        }

        if (connection === 'close') {
            const statusCode = (lastDisconnect?.error)?.output?.statusCode;
            const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
            connectionStatus = 'DISCONNECTED';
            currentQrCodeDataUrl = null;
            connectedNumber = null;
            console.log(`❌ [WhatsApp Bridge] Déconnecté (Code: ${statusCode}). Reconnexion: ${shouldReconnect}`);
            if (shouldReconnect) {
                setTimeout(startWhatsApp, 3000);
            }
        } else if (connection === 'open') {
            connectionStatus = 'CONNECTED';
            currentQrCodeDataUrl = null;
            connectedNumber = sock.user?.id ? sock.user.id.split(':')[0] : 'Inconnu';
            console.log(`✅ [WhatsApp Bridge] WhatsApp connecté avec succès au numéro: +${connectedNumber}`);
        }
    });

    // Écouter les messages entrants réels de WhatsApp
    sock.ev.on('messages.upsert', async (m) => {
        if (m.type !== 'notify') return;

        for (const msg of m.messages) {
            if (msg.key.fromMe) continue; // Ignorer les messages envoyés par nous-mêmes

            const remoteJid = msg.key.remoteJid;
            if (!remoteJid || remoteJid.includes('@g.us') || remoteJid === 'status@broadcast') continue; // Uniquement messages directs (pas de groupes)

            const senderPhone = remoteJid.split('@')[0];
            const senderName = msg.pushName || '';

            let userText = '';
            if (msg.message?.conversation) {
                userText = msg.message.conversation;
            } else if (msg.message?.extendedTextMessage?.text) {
                userText = msg.message.extendedTextMessage.text;
            } else if (msg.message?.buttonsResponseMessage?.selectedDisplayText) {
                userText = msg.message.buttonsResponseMessage.selectedDisplayText;
            } else if (msg.message?.listResponseMessage?.title) {
                userText = msg.message.listResponseMessage.title;
            }

            if (!userText || !userText.trim()) continue;

            console.log(`📩 [WhatsApp Inbound] Message de +${senderPhone} (${senderName}): "${userText.trim()}"`);

            // Transmettre à l'agent IA via le format Webhook WhatsApp officiel
            const payload = {
                object: 'whatsapp_business_account',
                entry: [{
                    id: 'BAILEYS_GATEWAY',
                    changes: [{
                        field: 'messages',
                        value: {
                            messaging_product: 'whatsapp',
                            metadata: {
                                display_phone_number: connectedNumber,
                                phone_number_id: 'baileys_gateway'
                            },
                            contacts: [{
                                profile: { name: senderName },
                                wa_id: senderPhone
                            }],
                            messages: [{
                                from: senderPhone,
                                id: msg.key.id,
                                timestamp: String(Math.floor(Date.now() / 1000)),
                                text: { body: userText.trim() },
                                type: 'text'
                            }]
                        }
                    }]
                }]
            };

            try {
                const fetch = (await import('node-fetch')).default || globalThis.fetch;
                await fetch(AI_WEBHOOK_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            } catch (postErr) {
                console.error(`Erreur transfert Webhook vers Commercial IA: ${postErr.message}`);
            }
        }
    });
}

// Routes HTTP pour piloter la passerelle depuis le tableau de bord Commercial IA
app.get('/status', (req, res) => {
    res.json({
        status: connectionStatus,
        number: connectedNumber,
        hasQr: !!currentQrCodeDataUrl
    });
});

app.get('/qr', (req, res) => {
    if (connectionStatus === 'CONNECTED') {
        return res.json({ connected: true, number: connectedNumber, status: 'CONNECTED' });
    }
    if (!currentQrCodeDataUrl) {
        return res.json({ connected: false, status: connectionStatus, message: 'Initialisation du QR Code en cours...' });
    }
    res.json({
        connected: false,
        status: 'SCAN_QR',
        qrDataUrl: currentQrCodeDataUrl
    });
});

app.post('/send', async (req, res) => {
    const { phone, text } = req.body;
    if (!phone || !text) {
        return res.status(400).json({ success: false, error: 'Paramètres phone et text requis' });
    }
    if (connectionStatus !== 'CONNECTED' || !sock) {
        return res.status(503).json({ success: false, error: 'Passerelle WhatsApp non connectée (QR Code requis)' });
    }

    try {
        const cleanPhone = phone.replace(/[^0-9]/g, '');
        const jid = `${cleanPhone}@s.whatsapp.net`;
        const result = await sock.sendMessage(jid, { text });
        console.log(`📤 [WhatsApp Outbound] Message envoyé avec succès à +${cleanPhone}`);
        res.json({ success: true, messageId: result.key.id });
    } catch (sendErr) {
        console.error(`Erreur envoi message WhatsApp: ${sendErr.message}`);
        res.status(500).json({ success: false, error: sendErr.message });
    }
});

app.post('/logout', async (req, res) => {
    try {
        if (sock) {
            await sock.logout();
        }
        if (fs.existsSync(AUTH_DIR)) {
            fs.rmSync(AUTH_DIR, { recursive: true, force: true });
        }
        setTimeout(startWhatsApp, 2000);
        res.json({ success: true, message: 'Session WhatsApp réinitialisée' });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.listen(PORT, () => {
    console.log(`🚀 [WhatsApp Bridge] Service écoute sur le port ${PORT}`);
    startWhatsApp();
});
