#!/bin/bash
# Test the monitoring and deployment scripts

echo "========================================"
echo "🧪 TESTING PERLFLOWS SCRIPTS"
echo "========================================"

# Make scripts executable
chmod +x /mnt/c/kyraProyecto/scripts/monitor-logs.sh
chmod +x /mnt/c/kyraProyecto/scripts/quick-deploy.sh

echo "✅ Scripts made executable"

# Test if scripts have correct syntax
echo ""
echo "🔍 Testing script syntax..."

echo "Testing monitor-logs.sh..."
bash -n /mnt/c/kyraProyecto/scripts/monitor-logs.sh
if [ $? -eq 0 ]; then
    echo "✅ monitor-logs.sh syntax OK"
else
    echo "❌ monitor-logs.sh syntax error"
fi

echo "Testing quick-deploy.sh..."
bash -n /mnt/c/kyraProyecto/scripts/quick-deploy.sh
if [ $? -eq 0 ]; then
    echo "✅ quick-deploy.sh syntax OK"
else
    echo "❌ quick-deploy.sh syntax error"
fi

echo ""
echo "📋 Scripts ready for VPS deployment"
echo "📝 To deploy to VPS:"
echo "   1. Copy scripts to VPS: scp scripts/*.sh perlflow@your-vps:/home/perlflow/"
echo "   2. Make executable: chmod +x /home/perlflow/*.sh"
echo "   3. Run: ./monitor-logs.sh or ./quick-deploy.sh"

echo ""
echo "🔧 Current systemd service should be running:"
echo "   sudo systemctl status perlflow"
echo "   sudo systemctl enable perlflow  # Para auto-start en boot"