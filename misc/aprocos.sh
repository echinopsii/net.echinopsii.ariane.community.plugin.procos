#!/bin/sh

case "$1" in
    start)
        if [ $EUID -ne 0 ]; then
           echo "[WARNING] $0 is not running as root but $USER..."
           echo "[WARNING] It will not be abble to map all process on this OS and may have some problems with the logs..."
        fi
        echo "Starting Ariane ProcOS"
        python3 -m ariane_procos &
        echo $! > /tmp/aprocos.pid
        ;;
    stop)
        if [ -f /tmp/aprocos.pid ]; then
            echo "Stopping Ariane ProcOS"
            cat /tmp/aprocos.pid | xargs kill
            rm /tmp/aprocos.pid
        else
            echo "Ariane ProcOS not started..."
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop}"
        exit 1
        ;;
esac

