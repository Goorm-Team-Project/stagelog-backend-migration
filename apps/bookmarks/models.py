from django.db import models

class Bookmark(models.Model):
    #ERD: bookmark_id INT PK
    bookmark_id = models.BigAutoField(primary_key=True)

    user_id = models.BigIntegerField()
    event_id = models.BigIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bookmark"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "event_id"], name="uq_bookmark_user_event")
        
        ]
    
    def __str__(self):
        return f"Bookmark(user_id={self.user_id}, event_id={self.event_id})"
