# 🚗 CarShare

A private car-sharing platform for small communities — family, friends, or colleagues. Owners list their cars, borrowers reserve them, and everything from booking to approval runs through one clean web app.

Built as a **Progressive Web App (PWA)** — installable on iPhone, Android, and desktop directly from the browser.

---

## ✨ Features

### For borrowers
- Reserve cars by selecting a date range, planning a route with stops, and calculating the estimated cost
- Real-time distance and cost estimation via route planning
- Booking status tracking (pending → accepted / declined)
- Send reminders to owners for pending bookings (rate-limited to once per 24h)
- Reschedule or cancel existing bookings
- Waitlist for unavailable cars — get notified when a spot opens
- Ride history with statistics: total rides, km driven, amount spent, and favourite car

### For owners
- Add and manage cars with name, description, and photo gallery
- Manual or **auto-calculated pricing** based on fuel type:
  - ⚡ **Electric:** battery capacity (kWh) + range (km) + charge cost per kWh
  - ⛽ **Combustion:** fuel consumption (L/100km) + fuel price per liter
- Block unavailable date ranges per car
- Accept or decline booking requests
- Shared ownership — invite co-owners by email to help manage a car

### General
- Push notifications + email notifications, configurable per event type in your profile
- In-app notification bell with unread count
- Bilingual interface: 🇳🇱 Dutch and 🇬🇧 English
- Car availability calendar
- Admin panel for approving new user registrations

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3 + Vite, PrimeVue, Tailwind CSS, Pinia |
| Backend | Python, FastAPI, SQLModel, SQLite |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Push notifications | Web Push (pywebpush) |
| Reverse proxy | Caddy (automatic HTTPS) |
| Deployment | Docker Compose |

---

## 🚀 Self-hosting

### Prerequisites
- Docker + Docker Compose
- A domain name pointed to your server

### 1. Clone the repository

```bash
git clone https://github.com/RenzoDaal/CarShare.git
cd CarShare
```

### 2. Create the `.env` file

Create a `.env` file in the project root:

```env
SECRET_KEY=your-very-secret-key
VAPID_PRIVATE_KEY=your-vapid-private-key
VAPID_PUBLIC_KEY=your-vapid-public-key
VAPID_CLAIM_EMAIL=mailto:you@example.com
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=you@example.com
SMTP_PASSWORD=your-smtp-password
SMTP_FROM=CarShare <you@example.com>
```

**Generate a VAPID key pair** (required for push notifications):
```bash
npx web-push generate-vapid-keys
```

### 3. Configure your domain

Edit `Caddyfile` and replace `carshare.services` with your own domain:

```
your.domain.com {
    ...
}
```

### 4. Create the data directory

The SQLite database and uploaded images are stored outside the container:

```bash
mkdir -p ~/carshare-data
```

Update the volume path in `docker-compose.yml` if needed:
```yaml
volumes:
  - /path/to/your/data:/app/data
```

### 5. Build and start

```bash
docker compose up --build -d
```

Caddy handles HTTPS automatically via Let's Encrypt.

### 6. Create the first admin user

After first startup, register an account through the web interface. Then promote it to admin directly in the database:

```bash
sqlite3 ~/carshare-data/carshare.db "UPDATE user SET is_approved=1, is_admin=1 WHERE email='you@example.com';"
```

From that point on, new registrations can be approved through the admin panel in the app.

---

## 📁 Project Structure

```
CarShare/
├── backend/
│   ├── main.py           # FastAPI app entry point
│   ├── models.py         # SQLModel database models
│   ├── schemas.py        # Pydantic request/response schemas
│   ├── auth.py           # JWT authentication
│   ├── database.py       # DB init + migrations
│   ├── emailer.py        # Email notifications
│   ├── utils.py          # Shared helpers
│   └── routers/          # API route handlers
│       ├── bookings.py
│       ├── cars.py
│       ├── users.py
│       └── notifications.py
├── frontend/
│   ├── src/
│   │   ├── pages/        # Vue page components
│   │   ├── components/   # Reusable UI components
│   │   ├── stores/       # Pinia state stores
│   │   ├── i18n/         # nl.json + en.json translations
│   │   └── router.ts     # Vue Router with auth guards
│   └── public/           # PWA icons, service worker
├── Caddyfile             # Reverse proxy config
└── docker-compose.yml
```

---

## 📄 License

Private project — not licensed for public use or redistribution.
