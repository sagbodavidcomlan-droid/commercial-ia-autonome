module.exports = {
  apps: [{
    name: 'n8n',
    script: 'n8n',
    args: 'start',
    env: {
      N8N_USER_FOLDER: process.env.HOME + '/.n8n',
      N8N_BASIC_AUTH_ACTIVE: 'true',
      N8N_BASIC_AUTH_USER: 'admin',
      N8N_BASIC_AUTH_PASSWORD: 'change_me_123',
      N8N_HOST: '0.0.0.0',
      N8N_PORT: '5678',
      WEBHOOK_URL: 'http://localhost:5678'
    },
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
  }]
};
