from django.conf import settings


class ServiceDbRouter:
    """
    App label 기준으로 DB alias를 분기한다.
    - auth schema: users + django auth 계열
    - events schema: events
    - core schema(default): 그 외 앱
    """

    AUTH_APP_LABELS = {"users", "auth", "admin", "contenttypes"}
    EVENTS_APP_LABELS = {"events"}
    SHARED_APP_LABELS = {"common"}

    def _target_db(self, app_label: str) -> str:
        dbs = settings.DATABASES.keys()

        if app_label in self.AUTH_APP_LABELS and "auth_db" in dbs:
            return "auth_db"
        if app_label in self.EVENTS_APP_LABELS and "events_db" in dbs:
            return "events_db"
        return "default"

    def db_for_read(self, model, **hints):
        return self._target_db(model._meta.app_label)

    def db_for_write(self, model, **hints):
        return self._target_db(model._meta.app_label)

    def allow_relation(self, obj1, obj2, **hints):
        db1 = self._target_db(obj1._meta.app_label)
        db2 = self._target_db(obj2._meta.app_label)
        if db1 == db2:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.SHARED_APP_LABELS:
            return db in {"default", "auth_db", "events_db"}
        return db == self._target_db(app_label)
