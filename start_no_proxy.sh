#!/bin/bash

# Отключаем proxy для localhost
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
export no_proxy="localhost,127.0.0.1,::1"
export NO_PROXY="localhost,127.0.0.1,::1"

echo "🔧 Proxy отключен для localhost"
echo "📍 no_proxy=$no_proxy"
echo ""

# Запускаем обычный start.sh
cd "/home/mego/Python Projects/THE_BOT_platform"
./start.sh
