# String constants.
# Other than top-of-page messages; those are found in msg_consts.py.
from django.utils.translation import ugettext_lazy as _

CONTACT_EMAIL_SUBJECT_FMTSTR = _(u"Contact Us - {username} - {base_subject}")
CONTACT_EMAIL_MESSAGE_FMTSTR = _(u"This email was sent using the Contact Us form.\n"
                                 u"\n"
                                 u"Username: {username}\n"
                                 u"User's email: {user_email}\n"
                                 u"\n"
                                 u"{base_message}")