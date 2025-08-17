#!/bin/bash
# Complete production health check for PerlFlows

echo "========================================"
echo "🏥 PERLFLOWS PRODUCTION HEALTH CHECK"
echo "========================================"
echo "🕐 $(date)"
echo ""

# Check if we're on VPS
if [[ "$HOSTNAME" == *"srv"* ]]; then
    echo "🖥️  Running on VPS: $HOSTNAME"
    IS_VPS=true
else
    echo "💻 Running on Local: $HOSTNAME"
    IS_VPS=false
fi

echo ""
echo "📊 SYSTEM STATUS:"
echo "----------------------------------------"

if [ "$IS_VPS" = true ]; then
    # VPS-specific checks
    echo "🔧 PerlFlow Service:"
    if systemctl is-active --quiet perlflow; then
        echo "   ✅ Service is running"
        echo "   📈 Uptime: $(systemctl show perlflow --property=ActiveEnterTimestamp --value | cut -d' ' -f2-)"
    else
        echo "   ❌ Service is not running"
        echo "   🔧 Try: sudo systemctl start perlflow"
    fi
    
    echo ""
    echo "🌐 Nginx Status:"
    if systemctl is-active --quiet nginx; then
        echo "   ✅ Nginx is running"
    else
        echo "   ❌ Nginx is not running"
    fi
    
    echo ""
    echo "📊 Resource Usage:"
    echo "   CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
    echo "   RAM: $(free -h | awk 'NR==2{printf "%.1f/%.1f GB (%.2f%%)", $3/1024/1024, $2/1024/1024, $3*100/$2}')"
    echo "   Disk: $(df -h / | awk 'NR==2{print $3"/"$2" ("$5")"}')"
    
    echo ""
    echo "🔐 Process Check:"
    PYTHON_PROCESSES=$(ps aux | grep -c "[p]ython.*main.py")
    echo "   Python processes: $PYTHON_PROCESSES"
    if [ $PYTHON_PROCESSES -gt 0 ]; then
        echo "   ✅ Application is running"
    else
        echo "   ❌ No Python application found"
    fi
fi

echo ""
echo "🌍 API ENDPOINTS:"
echo "----------------------------------------"

# Test health endpoint
echo "🔍 Health Check:"
HEALTH_RESPONSE=$(curl -s -w "%{http_code}" http://perlflow.com/api/health -o /tmp/health_response)
HTTP_CODE=$(tail -n1 <<< "$HEALTH_RESPONSE")

if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✅ API Health: OK ($HTTP_CODE)"
    HEALTH_CONTENT=$(cat /tmp/health_response)
    if [[ "$HEALTH_CONTENT" == *"ok"* ]]; then
        echo "   ✅ Health response: Valid"
    else
        echo "   ⚠️  Health response: Unexpected format"
    fi
else
    echo "   ❌ API Health: Failed ($HTTP_CODE)"
fi

# Test connectors endpoint
echo ""
echo "🔌 Connectors Endpoint:"
CONNECTORS_RESPONSE=$(curl -s -w "%{http_code}" http://perlflow.com/api/connectors -o /tmp/connectors_response)
HTTP_CODE=$(tail -n1 <<< "$CONNECTORS_RESPONSE")

if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✅ Connectors: OK ($HTTP_CODE)"
    CONNECTOR_COUNT=$(cat /tmp/connectors_response | jq length 2>/dev/null || echo "unknown")
    echo "   📊 Available connectors: $CONNECTOR_COUNT"
else
    echo "   ❌ Connectors: Failed ($HTTP_CODE)"
fi

# Test frontend
echo ""
echo "🎨 Frontend Check:"
FRONTEND_RESPONSE=$(curl -s -w "%{http_code}" http://perlflow.com -o /tmp/frontend_response)
HTTP_CODE=$(tail -n1 <<< "$FRONTEND_RESPONSE")

if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✅ Frontend: OK ($HTTP_CODE)"
    if grep -q "QYRAL\|PerlFlow" /tmp/frontend_response; then
        echo "   ✅ Frontend content: Valid"
    else
        echo "   ⚠️  Frontend content: Unexpected"
    fi
else
    echo "   ❌ Frontend: Failed ($HTTP_CODE)"
fi

# Response time test
echo ""
echo "⚡ PERFORMANCE:"
echo "----------------------------------------"
HEALTH_TIME=$(curl -w "%{time_total}s" -s -o /dev/null http://perlflow.com/api/health)
FRONTEND_TIME=$(curl -w "%{time_total}s" -s -o /dev/null http://perlflow.com)

echo "🏥 Health endpoint: $HEALTH_TIME"
echo "🎨 Frontend: $FRONTEND_TIME"

# Log check
if [ "$IS_VPS" = true ]; then
    echo ""
    echo "📋 RECENT LOGS:"
    echo "----------------------------------------"
    LOG_FILE="/home/perlflow/PerlFlows/logs/qyral_app_$(date +%Y-%m-%d).log"
    if [ -f "$LOG_FILE" ]; then
        echo "📄 Today's log file exists"
        LOG_LINES=$(wc -l < "$LOG_FILE" 2>/dev/null || echo "0")
        echo "📊 Log entries today: $LOG_LINES"
        
        echo ""
        echo "🔍 Last 3 log entries:"
        sudo -u perlflow tail -3 "$LOG_FILE" 2>/dev/null || echo "   No recent logs"
    else
        echo "❌ No log file for today"
    fi
    
    # Error log check
    ERROR_FILE="/home/perlflow/PerlFlows/logs/errors_$(date +%Y-%m-%d).log"
    if [ -f "$ERROR_FILE" ]; then
        ERROR_COUNT=$(wc -l < "$ERROR_FILE" 2>/dev/null || echo "0")
        if [ "$ERROR_COUNT" -gt 0 ]; then
            echo ""
            echo "⚠️  Errors today: $ERROR_COUNT"
            echo "🔍 Latest error:"
            sudo -u perlflow tail -1 "$ERROR_FILE" 2>/dev/null
        else
            echo ""
            echo "✅ No errors today"
        fi
    else
        echo ""
        echo "✅ No error log (good sign)"
    fi
fi

echo ""
echo "📋 SUMMARY:"
echo "----------------------------------------"

# Overall health score
SCORE=0
MAX_SCORE=4

# Check API health
if [ "$HTTP_CODE" = "200" ]; then
    SCORE=$((SCORE + 1))
fi

# Check if service is running (VPS only)
if [ "$IS_VPS" = true ]; then
    if systemctl is-active --quiet perlflow; then
        SCORE=$((SCORE + 1))
    fi
    if systemctl is-active --quiet nginx; then
        SCORE=$((SCORE + 1))
    fi
    MAX_SCORE=6
fi

# Check frontend
FRONTEND_RESPONSE=$(curl -s -w "%{http_code}" http://perlflow.com -o /dev/null)
if [ "$FRONTEND_RESPONSE" = "200" ]; then
    SCORE=$((SCORE + 1))
fi

PERCENTAGE=$((SCORE * 100 / MAX_SCORE))

if [ $PERCENTAGE -ge 90 ]; then
    echo "✅ System Health: EXCELLENT ($SCORE/$MAX_SCORE - $PERCENTAGE%)"
elif [ $PERCENTAGE -ge 70 ]; then
    echo "⚠️  System Health: GOOD ($SCORE/$MAX_SCORE - $PERCENTAGE%)"
elif [ $PERCENTAGE -ge 50 ]; then
    echo "🔧 System Health: NEEDS ATTENTION ($SCORE/$MAX_SCORE - $PERCENTAGE%)"
else
    echo "❌ System Health: CRITICAL ($SCORE/$MAX_SCORE - $PERCENTAGE%)"
fi

echo ""
echo "🛠️  QUICK FIXES:"
if [ "$IS_VPS" = true ]; then
    echo "   📋 Monitor logs: ./monitor-logs.sh"
    echo "   🚀 Quick deploy: ./quick-deploy.sh"
    echo "   🔧 Restart service: sudo systemctl restart perlflow"
    echo "   📊 Enable auto-start: sudo systemctl enable perlflow"
else
    echo "   🔌 Connect to VPS for full diagnostics"
fi

# Cleanup
rm -f /tmp/health_response /tmp/connectors_response /tmp/frontend_response 2>/dev/null

echo ""
echo "=========================================="