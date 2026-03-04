FROM php:8.4-cli

# System dependencies + intl (required by Filament)
RUN apt-get update && apt-get install -y \
    git \
    curl \
    zip \
    unzip \
    libpq-dev \
    libzip-dev \
    libicu-dev \
    && docker-php-ext-install pdo pdo_pgsql zip pcntl posix intl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Redis extension
RUN pecl install redis && docker-php-ext-enable redis

# Composer
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

WORKDIR /var/www/html

# Install dependencies (cached layer if composer.json unchanged)
COPY composer.json composer.lock ./
RUN composer install --no-scripts --no-autoloader --prefer-dist \
    --ignore-platform-req=ext-pcntl \
    --ignore-platform-req=ext-posix

# Copy app source
COPY . .
RUN composer dump-autoload --optimize

EXPOSE 8000

CMD ["php", "artisan", "serve", "--host=0.0.0.0", "--port=8000"]
