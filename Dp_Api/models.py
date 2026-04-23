from django.db import models

# Create your models here.
import uuid
import time
from django.db import models

# -------- UUID v7 generator (simple version) --------
def uuid7():
    ts_ms = int(time.time() * 1000)
    rand = uuid.uuid4().int & ((1 << 80) - 1)
    value = (ts_ms << 80) | rand
    return uuid.UUID(int=value)

# -------- Profile Model --------
class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    name = models.CharField(max_length=255, unique=True)
    gender = models.CharField(max_length=10)
    gender_probability = models.FloatField()
    age = models.IntegerField()
    age_group = models.CharField(max_length=20)
    country_id = models.CharField(max_length=2)
    country_name = models.CharField(max_length=100)
    country_probability = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name