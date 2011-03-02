import datetime

from django.conf import settings

from backtrac.server.storage import Storage, ClientStorage
from backtrac.apps.clients import models as client_models
from backtrac.apps.clients.models import client_connected, client_disconnected
from backtrac.apps.catalog.models import Item, Version, RestoreJob, \
        item_created, item_updated, item_deleted
from backtrac.utils import generate_version_id

def get_client(hostname):
    try:
        client_obj = client_models.Client.objects.get(hostname=hostname)
        return Client(client_obj)
    except client_models.Client.DoesNotExist:
        return None

class Client(object):
    def __init__(self, client_obj):
        self.client_obj = client_obj

    def connected(self):
        client_connected.send(sender=self.client_obj, client=self.client_obj)

    def disconnected(self):
        client_disconnected.send(sender=self.client_obj, client=self.client_obj)

    def get_hostname(self):
        return self.client_obj.hostname

    def get_key(self):
        return self.client_obj.secret_key

    def get_storage(self):
        storage = Storage(settings.BACKTRAC_BACKUP_ROOT)
        return ClientStorage(storage, self.client_obj)

    def get_paths(self):
        return [p.path for p in self.client_obj.filepaths.all()]

    def get_present_state(self, path):
        def get_children(item, items):
            items.append(item.path)
            for i in item.children.present():
                get_children(i, items)
        items = []
        try:
            item = Item.objects.get(client=self.client_obj, path=path)
            get_children(item, items)
        except catalog.Item.DoesNotExist:
            pass
        return items

    def create_item(self, path, type):
        item_created.send(sender=self.client_obj, path=path, type=type,
                          client=self.client_obj)

    def update_item(self, path, mtime, size, version_id):
        item_updated.send(sender=self.client_obj, path=path, mtime=mtime,
                          size=size, client=self.client_obj,
                          version_id=version_id)

    def delete_item(self, path):
        item_deleted.send(sender=self.client_obj, path=path,
                          client=self.client_obj)

    def backup_required(self, path, size, mtime):
        try:
            item = Item.objects.get(client=self.client_obj, path=path)
            if not item.latest_version or item.deleted:
                return True
            if abs(mtime - item.latest_version.mtime) < 1:
                if abs(size - item.latest_version.size) < 1:
                    return False
        except Item.DoesNotExist:
            pass
        return True

    def get_pending_restore_jobs(self):
        jobs = self.client_obj.restores.filter(started_at=None, completed_at=None)
        return [
            (job.id, job.version.item.path, job.version.id) for job in jobs
        ]

    def restore_begin(self, restore_id):
        try:
            job = RestoreJob.objects.get(id=restore_id)
            job.started_at = datetime.datetime.now()
            job.save()
            # copy the version to the latest slot so the restored file is not
            # backed up again
            version = job.version
            version.id = generate_version_id()
            version.backed_up_at = datetime.datetime.now()
            # TODO: re-enable this when the muter has been implemented
            #version.save()
        except RestoreJob.DoesNotExist:
            pass

    def restore_complete(self, restore_id):
        try:
            job = RestoreJob.objects.get(id=restore_id)
            job.completed_at = datetime.datetime.now()
            job.save()
        except RestoreJob.DoesNotExist:
            pass