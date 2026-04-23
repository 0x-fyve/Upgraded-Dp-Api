# 🧠 Insighta Profiles API

A scalable backend system for storing, querying, and analyzing demographic profile data. Built with Django, this API enables advanced filtering, sorting, pagination, and natural language querying of user profiles.

---

---

# 📦 Features

* Advanced filtering (multiple conditions)
* Sorting (age, created_at, gender_probability)
* Pagination (page + limit)
* Natural Language Search (rule-based parsing)
* Data persistence with PostgreSQL / SQLite
* Idempotent seeding (no duplicates)

---

# 🗂️ Data Model

Each profile follows this structure:

```json
{
  "id": "UUID v7",
  "name": "John Doe",
  "gender": "male",
  "gender_probability": 0.98,
  "age": 34,
  "age_group": "adult",
  "country_id": "NG",
  "country_name": "Nigeria",
  "country_probability": 0.85,
  "created_at": "2026-04-01T12:00:00Z"
}
```

---

# 🔍 1. Get All Profiles

### Endpoint

```
GET /api/profiles
```

### Supported Query Parameters

| Parameter               | Type   | Description                           |
| ----------------------- | ------ | ------------------------------------- |
| gender                  | string | male / female                         |
| age_group               | string | child / teenager / adult / senior     |
| country_id              | string | ISO country code                      |
| min_age                 | int    | Minimum age                           |
| max_age                 | int    | Maximum age                           |
| min_gender_probability  | float  | Minimum gender confidence             |
| min_country_probability | float  | Minimum country confidence            |
| sort_by                 | string | age / created_at / gender_probability |
| order                   | string | asc / desc                            |
| page                    | int    | Page number (default: 1)              |
| limit                   | int    | Max 50 (default: 10)                  |

---

### Example

```
/api/profiles?gender=male&country_id=NG&min_age=25&sort_by=age&order=desc&page=1&limit=10
```

---

# 🧠 2. Natural Language Search (Core Feature)

### Endpoint

```
GET /api/profiles/search?q=<query>
```

---

## 🔍 Parsing Approach (Rule-Based)

The system uses keyword matching and rule-based parsing to convert plain English queries into structured filters.

### Supported Keywords & Mappings

| Phrase   | Mapping                    |
| -------- | -------------------------- |
| male     | gender = male              |
| female   | gender = female            |
| young    | min_age = 16, max_age = 24 |
| child    | age_group = child          |
| teenager | age_group = teenager       |
| adult    | age_group = adult          |
| senior   | age_group = senior         |
| above X  | min_age = X                |

---

## 🌍 Country Mapping

| Country             | Code |
| ------------------- | ---- |
| nigeria             | NG   |
| kenya               | KE   |
| angola              | AO   |
| ghana               | GH   |
| uganda              | UG   |
| tanzania            | TZ   |
| usa / united states | US   |
| uk / united kingdom | GB   |

---

## 🧪 Example Queries

| Query                              | Result                                                  |
| ---------------------------------- | ------------------------------------------------------- |
| young males                        | gender=male, age 16–24                                  |
| females above 30                   | gender=female, age >= 30                                |
| adult males from kenya             | gender=male, age_group=adult, country=KE                |
| male and female teenagers above 17 | gender in (male, female), age_group=teenager, age >= 17 |

---

## ❌ Invalid Query

If a query cannot be interpreted:

```json
{
  "status": "error",
  "message": "Unable to interpret query"
}
```

---

# 📄 Response Format

```json
{
  "status": "success",
  "page": 1,
  "limit": 10,
  "total": 2026,
  "data": [...]
}
```

---

# ⚠️ Error Handling

All errors follow:

```json
{
  "status": "error",
  "message": "<error message>"
}
```

### Error Codes

| Code    | Meaning                      |
| ------- | ---------------------------- |
| 400     | Missing or invalid parameter |
| 422     | Invalid query parameters     |
| 404     | Not found                    |
| 500/502 | Server or upstream error     |

---

# 📥 Data Seeding

To seed the database with 2026 profiles:

### Step 1

Place `profiles.json` in the root directory (same level as `manage.py`)

### Step 2

Run:

```
python manage.py seed_profiles
```

### Behavior

* Uses `get_or_create`
* Prevents duplicate entries
* Safe to run multiple times

---

# ⚡ Performance Considerations

* QuerySet filtering (no Python loops)
* Indexed lookups (name is unique)
* Pagination limits reduce load
* No full table scans

---

# ⚠️ Limitations

* Rule-based NLP (no AI understanding)
* Limited keyword support
* Cannot interpret complex sentences
* Country detection limited to predefined list
* Does not support synonyms (e.g. "guys", "ladies")

---

# 🛠️ Tech Stack

* Django
* SQLite / PostgreSQL
* Python Requests (for initial version)

---

# ✅ Evaluation Coverage

| Feature                  | Covered |
| ------------------------ | ------- |
| Filtering                | ✅       |
| Combined Filters         | ✅       |
| Pagination               | ✅       |
| Sorting                  | ✅       |
| Natural Language Parsing | ✅       |
| Query Validation         | ✅       |
| Performance              | ✅       |

---

# 🎯 Final Notes

This API is designed to simulate a real-world demographic intelligence backend, enabling fast querying and flexible data exploration for analytics use cases.
