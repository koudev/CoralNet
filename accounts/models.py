from django.db import models
from django.utils.translation import ugettext_lazy as _

from userena.models import UserenaLanguageBaseProfile

class Profile(UserenaLanguageBaseProfile):
   about_me = models.CharField(_('Name'), max_length=45, blank=True)
   website = models.URLField(_('Website'), blank=True, verify_exists=True)
   location =  models.CharField(_('Location'), max_length=45, blank=True)
  #  group = models.ForeignKey(Group)

#class Group(models.Model):
 #   name = models.CharField(max_length=45, blank=True)
  #  member_permission = choices("View", "Annotate", "None") #Default permissions for GROUP MEMBERS on GROUPS images
  #  source_permission = choices("View", "Annotate", "None") #Default permissions for EVERYONE ELSE on GROUPS images