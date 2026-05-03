# Правка nginx для bot-1c.ru (вставка в основной конфиг)

## Что было не так в показанном фрагменте

1. **Порт 80** — смешаны обработка `location /`, PHP и редирект. Для «только перевести всех на HTTPS» достаточно **одной** директивы `return`, без `root` и без `location`.
2. Редирект **`https://$host:443$request_uri`** — порт `:443` в URL обычно не пишут; используйте **`https://$host$request_uri`**.
3. Прокси на FastAPI (**`/api/`**, **`/health`**) нужны **только в `server` с SSL (443)**. В блок на **80** их не добавляют.

Если раньше в HTTPS у вас были **try_files**, **статика** и **`@fallback` на :8080**, после правок они могли пропасть — восстановите из резервной копии или из панели, и вставьте наши `location` **выше** общего `location /`, как в примере ниже.

---

## Готовый исправленный вариант

### HTTP — только редирект на HTTPS

```nginx
server {
	listen 157.22.252.143:80;
	server_name bot-1c.ru www.bot-1c.ru;
	return 301 https://$host$request_uri;
}
```

Проверка: `curl -I http://bot-1c.ru` → должно быть `301` и `Location: https://bot-1c.ru/...`.

---

### HTTPS — ваш контент + API портала

Ниже пример **полного** `server { ... }` для 443: сохранены ваши пути к сертификатам, `root`, PHP и логи; **добавлены** три `location` сразу после `root` (перед `location /`). Если главную отдаёт не статический `index.html`, а сервис на :8080 — **удалите** блок `location = / { ... }`.

```nginx
server {
	server_name bot-1c.ru www.bot-1c.ru;
	listen 157.22.252.143:443 ssl;

	ssl_certificate "/var/www/httpd-cert/www-root/bot-1c.ru_le1.crt";
	ssl_certificate_key "/var/www/httpd-cert/www-root/bot-1c.ru_le1.key";
	ssl_ciphers EECDH:+AES256:-3DES:RSA+AES:!NULL:!RC4;
	ssl_prefer_server_ciphers on;
	ssl_protocols TLSv1.2 TLSv1.3;
	add_header Strict-Transport-Security "max-age=31536000;";
	ssl_dhparam /etc/ssl/certs/dhparam4096.pem;

	charset off;
	index index.php index.html;
	disable_symlinks if_not_owner from=$root_path;
	include /etc/nginx/vhosts-includes/*.conf;
	include /etc/nginx/vhosts-resources/bot-1c.ru/*.conf;
	access_log /var/www/httpd-logs/bot-1c.ru.access.log;
	error_log /var/www/httpd-logs/bot-1c.ru.error.log notice;
	ssi on;

	set $root_path /var/www/www-root/data/www/bot-1c.ru;
	root $root_path;

	location ^~ /api/ {
		proxy_pass http://127.0.0.1:8000;
		proxy_http_version 1.1;
		proxy_set_header Host $host;
		proxy_set_header X-Real-IP $remote_addr;
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_set_header X-Forwarded-Proto $scheme;
		proxy_read_timeout 120s;
	}

	location = /health {
		proxy_pass http://127.0.0.1:8000/health;
		proxy_http_version 1.1;
		proxy_set_header Host $host;
		proxy_set_header X-Forwarded-Proto $scheme;
	}

	location = / {
		root /var/www/www-root/data/www/bot-1c.ru;
		try_files /index.html =404;
	}

	location / {
		location ~ [^/]\.ph(p\d*|tml)$ {
			try_files /does_not_exists @php;
		}
	}

	location @php {
		include /etc/nginx/vhosts-resources/bot-1c.ru/dynamic/*.conf;
		fastcgi_index index.php;
		fastcgi_param PHP_ADMIN_VALUE "sendmail_path = /usr/sbin/sendmail -t -i -f webmaster@bot-1c.ru";
		fastcgi_pass unix:/var/www/php-fpm/2.sock;
		fastcgi_split_path_info ^((?U).+\.ph(?:p\d*|tml))(/?.+)$;
		try_files $uri =404;
		include fastcgi_params;
	}
}
```

Убедитесь, что backend запущен: `curl -s http://127.0.0.1:8000/health`.

Затем:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

Проверки:

```bash
curl -sS https://bot-1c.ru/health
curl -sS -o /dev/null -w "%{http_code}" https://bot-1c.ru/api/v1/me -H "Authorization: Bearer …"
```

Для Telegram задайте **`PUBLIC_BASE_URL=https://bot-1c.ru`**.

---

## Кратко: куда вставлять вручную

Если правите не целиком блок, а только добавляете строки — в **HTTPS** `server` вставьте **`location ^~ /api/`**, **`location = /health`** и при необходимости **`location = /`** сразу после **`root $root_path;`**, до **`location /`**.

В **HTTP** `server` на 80 — только **`return 301 https://$host$request_uri;`** (остальное из старого блока для :80 можно убрать).
