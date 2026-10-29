from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User


@receiver(post_save, sender=User)
def sync_user_role_group(sender, instance, **kwargs):
    """Keep each account's Django group aligned with its selected role."""
    role_group, _ = Group.objects.get_or_create(name=instance.role)
    role_groups = Group.objects.filter(name__in=User.Role.values)
    instance.groups.remove(*role_groups.exclude(pk=role_group.pk))
    instance.groups.add(role_group)
