let makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion, Browsers;

async function loadBaileys() {
    try {
        const baileys = await import('@whiskeysockets/baileys');
        makeWASocket = baileys.default || baileys.makeWASocket;
        useMultiFileAuthState = baileys.useMultiFileAuthState;
        DisconnectReason = baileys.DisconnectReason;
        fetchLatestBaileysVersion = baileys.fetchLatestBaileysVersion;
        Browsers = baileys.Browsers;
    } catch (importErr) {
        const baileys = require('@whiskeysockets/baileys');
        makeWASocket = baileys.default || baileys.makeWASocket;
        useMultiFileAuthState = baileys.useMultiFileAuthState;
        DisconnectReason = baileys.DisconnectReason;
        fetchLatestBaileysVersion = baileys.fetchLatestBaileysVersion;
        Browsers = baileys.Browsers;
    }
}
const pino = require('pino');
const express = require('express');
const qrcode = require('qrcode');
const path = require('path');
const fs = require('fs');

const app = express();
app.use(express.json());

const PORT = parseInt(process.env.WHATSAPP_BRIDGE_PORT || '3001', 10);
const HOST = '127.0.0.1';
const AI_WEBHOOK_URL = process.env.AI_WEBHOOK_URL || 'https://commercial-ia-autonome.onrender.com/webhook/whatsapp';
const AUTH_DIR = path.join(__dirname, 'auth_info_baileys');

app.get('/', (req, res) => {
    res.json({
        service: "WhatsApp Bridge Daemon (Internal)",
        status: connectionStatus,
        connectedNumber: connectedNumber,
        hasQr: !!currentQrCodeDataUrl
    });
});

let sock = null;
let currentQrCodeDataUrl = null;
let currentPairingCode = null;
let connectionStatus = 'DISCONNECTED'; // DISCONNECTED, SCAN_QR, CONNECTED
let connectedNumber = null;

async function startWhatsApp(pairingPhone = null) {
    if (!makeWASocket) {
        await loadBaileys();
    }
    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
    const { version } = await fetchLatestBaileysVersion();

    const browserSignature = (Browsers && typeof Browsers.ubuntu === 'function')
        ? Browsers.ubuntu('Chrome')
        : ['Ubuntu', 'Chrome', '22.04.4'];

    sock = makeWASocket({
        version,
        logger: pino({ level: 'silent' }),
        printQRInTerminal: false,
        auth: state,
        browser: browserSignature,
        syncFullHistory: false,
        connectTimeoutMs: 60000,
        defaultQueryTimeoutMs: 60000,
        keepAliveIntervalMs: 25000
    });

    sock.ev.on('creds.update', saveCreds);

    // Demander le Pairing Code uniquement si explicitement demandé par l'utilisateur
    if (!sock.authState.creds.registered && pairingPhone) {
        setTimeout(async () => {
            try {
                const cleanPhone = pairingPhone.replace(/[^0-9]/g, '');
                const code = await sock.requestPairingCode(cleanPhone);
                currentPairingCode = code;
                console.log(`\n======================================================`);
                console.log(`🔑 [CODE WHATSAPP OFFICIEL] : ${code}`);
                console.log(`======================================================\n`);
            } catch (err) {
                console.error('Erreur demande Pairing Code:', err.message);
            }
        }, 3000);
    }

    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            connectionStatus = 'SCAN_QR';
            try {
                currentQrCodeDataUrl = await qrcode.toDataURL(qr, { margin: 2, scale: 8 });
                const base64Data = currentQrCodeDataUrl.split(',')[1];
                const qrStaticPath = path.join(__dirname, '..', 'web', 'static', 'whatsapp_qr.png');
                try {
                    fs.writeFileSync(qrStaticPath, Buffer.from(base64Data, 'base64'));
                } catch (e) {}
            } catch (err) {
                console.error('Erreur génération QR:', err);
            }
        }

        if (connection === 'close') {
            const statusCode = (lastDisconnect?.error)?.output?.statusCode;
            connectionStatus = 'DISCONNECTED';
            currentPairingCode = null;
            currentQrCodeDataUrl = null;
            connectedNumber = null;
            console.log(`❌ [WhatsApp Bridge] Déconnecté (Code: ${statusCode})`);

            // Si déconnecté avant association complète, ou suite à déconnexion/rejet :
            // Nettoyage immédiat du cache pour repartir sur un QR Code 100% propre
            const isUnregistered = !sock?.authState?.creds?.registered;
            const isLoggedOut = statusCode === DisconnectReason.loggedOut || statusCode === 401 || statusCode === 403;

            if (isUnregistered || isLoggedOut) {
                console.log(`🧹 [WhatsApp Bridge] Session non enregistrée ou révoquée. Réinitialisation des clés et redémarrage propre...`);
                try {
                    if (fs.existsSync(AUTH_DIR)) {
                        fs.rmSync(AUTH_DIR, { recursive: true, force: true });
                    }
                } catch (cleanErr) {
                    console.error('Erreur nettoyage auth_info:', cleanErr);
                }
                setTimeout(() => startWhatsApp(null), 1500);
            } else {
                setTimeout(() => startWhatsApp(null), 3000);
            }
        } else if (connection === 'open') {
            connectionStatus = 'CONNECTED';
            currentPairingCode = null;
            currentQrCodeDataUrl = null;
            connectedNumber = sock.user?.id ? sock.user.id.split(':')[0] : 'Inconnu';
            console.log(`🎉 [WhatsApp Bridge] WhatsApp CONNECTÉ avec succès au numéro: +${connectedNumber}`);
        }
    });

    sock.ev.on('messages.upsert', async (m) => {
        if (m.type !== 'notify') return;

        for (const msg of m.messages) {
            if (msg.key.fromMe) continue;

            const remoteJid = msg.key.remoteJid;
            if (!remoteJid || remoteJid.includes('@g.us') || remoteJid === 'status@broadcast') continue;

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
                console.error(`Erreur transfert Webhook: ${postErr.message}`);
            }
        }
    });
}

app.get('/status', (req, res) => {
    res.json({
        status: connectionStatus,
        number: connectedNumber,
        hasQr: !!currentQrCodeDataUrl,
        pairingCode: currentPairingCode
    });
});

app.get('/pairing-code', (req, res) => {
    res.json({
        pairingCode: currentPairingCode,
        status: connectionStatus
    });
});

app.get('/qr', (req, res) => {
    if (connectionStatus === 'CONNECTED') {
        return res.json({ connected: true, number: connectedNumber, status: 'CONNECTED' });
    }
    res.json({
        connected: false,
        status: connectionStatus,
        pairingCode: currentPairingCode,
        qrDataUrl: currentQrCodeDataUrl
    });
});

app.post('/send', async (req, res) => {
    const { phone, text } = req.body;
    if (!phone || !text) return res.status(400).json({ success: false, error: 'Paramètres manquants' });
    if (connectionStatus !== 'CONNECTED' || !sock) return res.status(503).json({ success: false, error: 'Non connecté' });

    try {
        const cleanPhone = phone.replace(/[^0-9]/g, '');
        const jid = `${cleanPhone}@s.whatsapp.net`;
        const result = await sock.sendMessage(jid, { text });
        res.json({ success: true, messageId: result.key.id });
    } catch (sendErr) {
        res.status(500).json({ success: false, error: sendErr.message });
    }
});

app.post(['/logout', '/reset'], (req, res) => {
    try {
        if (sock) {
            try { sock.end(); } catch (e) {}
            sock = null;
        }
        if (fs.existsSync(AUTH_DIR)) {
            fs.rmSync(AUTH_DIR, { recursive: true, force: true });
        }
        connectionStatus = 'DISCONNECTED';
        connectedNumber = null;
        currentPairingCode = null;
        currentQrCodeDataUrl = null;
        res.json({ success: true, message: 'Session WhatsApp réinitialisée avec succès.' });
        setTimeout(() => startWhatsApp(null), 1000);
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/request-pairing-code', async (req, res) => {
    const { phone } = req.body;
    if (!phone) {
        return res.status(400).json({ success: false, error: 'Numéro de téléphone requis (ex: 229XXXXXXXX)' });
    }
    const cleanPhone = phone.replace(/[^0-9]/g, '');
    if (cleanPhone.length < 8) {
        return res.status(400).json({ success: false, error: 'Numéro de téléphone invalide' });
    }

    try {
        if (sock) {
            try { sock.end(); } catch (e) {}
            sock = null;
        }
        if (fs.existsSync(AUTH_DIR)) {
            fs.rmSync(AUTH_DIR, { recursive: true, force: true });
        }
        connectionStatus = 'DISCONNECTED';
        currentQrCodeDataUrl = null;
        currentPairingCode = null;

        await startWhatsApp(cleanPhone);

        // Attendre brièvement la génération du code
        let attempts = 0;
        while (!currentPairingCode && attempts < 12) {
            await new Promise(r => setTimeout(r, 500));
            attempts++;
        }

        if (currentPairingCode) {
            res.json({ success: true, pairingCode: currentPairingCode });
        } else {
            res.json({ success: true, message: 'Code en cours de génération, veuillez actualiser dans 2 secondes' });
        }
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.listen(PORT, HOST, () => {
    console.log(`🚀 [WhatsApp Bridge] Écoute strictement sur ${HOST}:${PORT}`);
    startWhatsApp(null); // Mode QR Code pur par défaut !
});
