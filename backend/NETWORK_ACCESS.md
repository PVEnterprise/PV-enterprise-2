# Network Access Configuration

This guide explains how to access the backend API from other devices on your network with HTTPS.

## Your Machine's IP Address
**Current IP: 192.168.1.2** (check with `ipconfig getifaddr en0`)

## Backend Setup

### 1. Update `.env` file
Edit your `.env` file and update the CORS settings:

```env
ALLOWED_ORIGINS=https://localhost:3000,https://192.168.1.2:3000
```

### 2. Start the Backend Server
Use the provided script to start the server with HTTPS:

```bash
./start_server.sh
```

Or manually run:
```bash
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --ssl-keyfile=certs/key.pem --ssl-certfile=certs/cert.pem
```

The backend will be accessible at:
- **Local**: https://localhost:8000
- **Network**: https://192.168.1.2:8000

## Frontend Setup

### Update Frontend API URL
Update your frontend configuration to use the network IP:

**For Vite/React (`.env` or `.env.local`):**
```env
VITE_API_URL=https://192.168.1.2:8000
```

### Start Frontend with Network Access
```bash
npm run dev -- --host 0.0.0.0
```

The frontend will be accessible at:
- **Local**: https://localhost:3000
- **Network**: https://192.168.1.2:3000

## Access from Other Devices

From any device on the same network:

1. **Backend API**: https://192.168.1.2:8000
2. **Frontend App**: https://192.168.1.2:3000
3. **API Docs**: https://192.168.1.2:8000/docs

## Firewall Settings

If you can't access from other devices, check your firewall:

**macOS:**
```bash
# Allow incoming connections on port 8000 and 5173
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/local/bin/uvicorn
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblock /usr/local/bin/uvicorn
```

Or go to: **System Preferences → Security & Privacy → Firewall → Firewall Options**

## Testing Network Access

From another device on the network, test:

```bash
# Test backend
curl http://172.20.7.91:8000/health

# Or open in browser
http://172.20.7.91:8000/docs
```

## Security Note

⚠️ **Important**: This configuration is for development only. For production:
- Use HTTPS
- Configure proper firewall rules
- Use environment-specific CORS settings
- Consider using a reverse proxy (nginx/Apache)
