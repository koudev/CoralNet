from django.conf import settings
from django.db import models

from django.contrib.auth.models import User
from easy_thumbnails.fields import ThumbnailerImageField
from guardian.shortcuts import get_objects_for_user, get_users_with_perms, get_perms, assign
from images.utils import PointGen
from CoralNet.utils import generate_random_filename

class Source(models.Model):

    class VisibilityTypes():
        PUBLIC = 'b'
        PUBLIC_VERBOSE = 'Public'
        PRIVATE = 'v'
        PRIVATE_VERBOSE = 'Private'

    # Example: 'Moorea'
    name = models.CharField(max_length=200, unique=True)

    VISIBILITY_CHOICES = (
        (VisibilityTypes.PUBLIC, VisibilityTypes.PUBLIC_VERBOSE),
        (VisibilityTypes.PRIVATE, VisibilityTypes.PRIVATE_VERBOSE),
    )
    visibility = models.CharField(max_length=1, choices=VISIBILITY_CHOICES, default=VisibilityTypes.PRIVATE)

    # Automatically set to the date and time of creation.
    create_date = models.DateTimeField('Date created', auto_now_add=True, editable=False)

    description = models.TextField(blank=True)

    labelset = models.ForeignKey('annotations.LabelSet')
    
    # Each of these fields is allowed to be blank (an empty string).
    # We're assuming that we'll only have key 2 if we have
    # key 1, we'll only have key 3 if we have key 2, etc.
    key1 = models.CharField('Key 1', max_length=50, blank=True)
    key2 = models.CharField('Key 2', max_length=50, blank=True)
    key3 = models.CharField('Key 3', max_length=50, blank=True)
    key4 = models.CharField('Key 4', max_length=50, blank=True)
    key5 = models.CharField('Key 5', max_length=50, blank=True)

    POINT_GENERATION_CHOICES = (
        (PointGen.Types.SIMPLE, PointGen.Types.SIMPLE_VERBOSE),
        (PointGen.Types.STRATIFIED, PointGen.Types.STRATIFIED_VERBOSE),
        (PointGen.Types.UNIFORM, PointGen.Types.UNIFORM_VERBOSE),
    )
    default_point_generation_method = models.CharField(
        'Point generation method',
        max_length=50,
        default=PointGen.args_to_db_format(
                    point_generation_type=PointGen.Types.SIMPLE,
                    simple_number_of_points=200)
    )

    longitude = models.CharField(max_length=20, blank=True)
    latitude = models.CharField(max_length=20, blank=True)

    #start_date = models.DateField(null=True, blank=True)
    #end_date = models.DateField(null=True, blank=True)

    class Meta:
        # Permissions for users to perform actions on Sources.
        # (Unfortunately, inner classes can't use outer-class
        # variables such as constants... so we've hardcoded these.)
        permissions = (
            ('source_view', 'View'),
            ('source_edit', 'Edit'),
            ('source_admin', 'Admin'),
        )

    class PermTypes:
        class ADMIN():
            code = 'source_admin'
            fullCode  = 'images.' + code
            verbose = 'Admin'
        class EDIT():
            code = 'source_edit'
            fullCode  = 'images.' + code
            verbose = 'Edit'
        class VIEW():
            code = 'source_view'
            fullCode  = 'images.' + code
            verbose = 'View'

    ##########
    # Database-query methods related to Sources
    ##########
    @staticmethod
    def get_public_sources():
        return Source.objects.filter(visibility=Source.VisibilityTypes.PUBLIC)

    @staticmethod
    def get_sources_of_user(user):
        # For superusers, this returns ALL sources.
        return get_objects_for_user(user, Source.PermTypes.VIEW.fullCode)

    @staticmethod
    def get_other_public_sources(user):
        return [source for source in Source.get_public_sources()
                if source not in Source.get_sources_of_user(user)]

    def has_member(self, user):
        return user in self.get_members()

    def get_members(self):
        return get_users_with_perms(self)

    def get_member_role(self, user):
        """
        Get a user's conceptual "role" in the source.

        If they have admin perms, their role is admin.
        Otherwise, if they have edit perms, their role is edit.
        Otherwise, if they have view perms, their role is view.
        Role is None if user is not a Source member.
        """
        perms = get_perms(user, self)

        for permType in [Source.PermTypes.ADMIN,
                         Source.PermTypes.EDIT,
                         Source.PermTypes.VIEW]:
            if permType.code in perms:
                return permType.verbose

    def assign_role(self, user, role):
        """
        Shortcut method to assign a conceptual "role" to a user,
        so assigning permissions can be done compactly.

        Admin role: admin, edit, view perms
        Edit role: edit, view perms
        View role: view perm
        """

        if role == Source.PermTypes.ADMIN.code:
            assign(Source.PermTypes.ADMIN.code, user, self)
            assign(Source.PermTypes.EDIT.code, user, self)
            assign(Source.PermTypes.VIEW.code, user, self)
        elif role == Source.PermTypes.EDIT.code:
            assign(Source.PermTypes.EDIT.code, user, self)
            assign(Source.PermTypes.VIEW.code, user, self)
        elif role == Source.PermTypes.VIEW.code:
            assign(Source.PermTypes.VIEW.code, user, self)
        else:
            raise ValueError("Invalid Source role: %s" % role)


    def visible_to_user(self, user):
        return (self.visibility == Source.VisibilityTypes.PUBLIC) or self.has_member(user)

    def get_all_images(self):
        return Image.objects.filter(source=self)
    
    def get_key_list(self):
        """
        Get a list of this Source's location keys.
        Just to be safe, only gets key n if keys 1 to n-1 are present.
        """

        keyList = []

        for k in ['key1', 'key2', 'key3', 'key4', 'key5']:
            if getattr(self,k):
                keyList.append(getattr(self,k))
            else:
                break

        return keyList

    def get_value_field_list(self):
        """
        If the source has 3 keys, this returns
        ['value1','value2','value3']
        Could be useful for forms when determining
        which metadata values apply to a given source.
        """
        valueFieldList = []
        
        for k,v in [('key1','value1'),
                    ('key2','value2'),
                    ('key3','value3'),
                    ('key4','value4'),
                    ('key5','value5'),]:
            if getattr(self,k):
                valueFieldList.append(v)

        return valueFieldList

    def num_of_keys(self):
        """
        Return the number of location keys that this Source has.
        """
        return len(self.get_key_list())

    def point_gen_method_display(self):
        """
        Display the point generation method in templates.
        Usage: {{ mysource.point_gen_method_display }}
        """
        return PointGen.db_to_readable_format(self.default_point_generation_method)

    def __unicode__(self):
        """
        To-string method.
        """
        return self.name


class SourceInvite(models.Model):
    """
    Invites will be deleted once they're accepted.
    """
    sender = models.ForeignKey(User, related_name='invites_sent', editable=False)
    recipient = models.ForeignKey(User, related_name='invites_received')
    source = models.ForeignKey(Source, editable=False)
    source_perm = models.CharField(max_length=50, choices=Source._meta.permissions)

    class Meta:
        # A user can only be invited once to a source.
        unique_together = ['recipient', 'source']


class LocationValue(models.Model):
    class Meta:
        # An abstract base class; no table will be created for
        # this class, but tables will be created for its sub-classes
        abstract = True

    name = models.CharField(max_length=50)
    source = models.ForeignKey(Source)

    def __unicode__(self):
        return self.name

class Value1(LocationValue):
    pass
class Value2(LocationValue):
    pass
class Value3(LocationValue):
    pass
class Value4(LocationValue):
    pass
class Value5(LocationValue):
    pass

class Metadata(models.Model):
    name = models.CharField(max_length=200, blank=True)
    photo_date = models.DateField('Photo date',
                                  help_text='Format: YYYY-MM-DD')

    latitude = models.CharField(max_length=20, blank=True)
    longitude = models.CharField(max_length=20, blank=True)
    depth = models.CharField(max_length=45, blank=True)

    # Do we need any input checking on pixel_cm_ratio?
    pixel_cm_ratio = models.CharField('Pixel/cm ratio', max_length=45, null=True, blank=True)
    camera = models.CharField(max_length=200, blank=True)
    photographer = models.CharField(max_length=45, blank=True)
    water_quality = models.CharField(max_length=45, blank=True)

    strobes = models.CharField(max_length=200, blank=True)
    framing = models.CharField('Framing gear used', max_length=200, blank=True)
    balance = models.CharField('White balance card', max_length=200, blank=True)
    
    comments = models.TextField(max_length=1000, blank=True)
    
    value1 = models.ForeignKey(Value1, null=True)
    value2 = models.ForeignKey(Value2, null=True)
    value3 = models.ForeignKey(Value3, null=True)
    value4 = models.ForeignKey(Value4, null=True)
    value5 = models.ForeignKey(Value5, null=True)
    group1_percent = models.IntegerField(default=0)
    group2_percent = models.IntegerField(default=0)
    group3_percent = models.IntegerField(default=0)
    group4_percent = models.IntegerField(default=0)
    group5_percent = models.IntegerField(default=0)
    group6_percent = models.IntegerField(default=0)
    group7_percent = models.IntegerField(default=0)

    def __unicode__(self):
        return "Metadata of " + self.name


def get_original_image_upload_path(instance, filename):
    """
    Generate a destination path (on the server filesystem) for
    a data-image upload.
    """
    return generate_random_filename(settings.ORIGINAL_IMAGE_DIR, filename, numOfChars=10)
    
class Image(models.Model):
    # width_field and height_field allow Django to cache the width and height values
    # so that the image file doesn't have to be read every time we want the width and height.
    # The cache is only updated when the image is saved.
    original_file = ThumbnailerImageField(
        upload_to=get_original_image_upload_path,
        width_field="original_width", height_field="original_height")

    # Cached width and height values for the file field.
    original_width = models.IntegerField()
    original_height = models.IntegerField()

    #TODO: Add another field for the processed image file.
    # Also add the corresponding width/height fields if we allow image cropping or resizing.

    upload_date = models.DateTimeField('Upload date', auto_now_add=True, editable=False)
    uploaded_by = models.ForeignKey(User, editable=False)
    status = models.CharField(max_length=1, blank=True)

    POINT_GENERATION_CHOICES = (
        (PointGen.Types.SIMPLE, PointGen.Types.SIMPLE_VERBOSE),
        (PointGen.Types.STRATIFIED, PointGen.Types.STRATIFIED_VERBOSE),
        (PointGen.Types.UNIFORM, PointGen.Types.UNIFORM_VERBOSE),
        (PointGen.Types.IMPORTED, PointGen.Types.IMPORTED_VERBOSE),
    )
    point_generation_method = models.CharField(
        'How points were generated',
        max_length=50,
        blank=True,
    )
    
    metadata = models.ForeignKey(Metadata)
    source = models.ForeignKey(Source)

    def __unicode__(self):
        return self.metadata.name

    # Use this as the "title" element of the image on an HTML page
    # (hover the mouse over the image to see this)
    def get_image_element_title(self):
        metadata = self.metadata
        dataStrings = []
        for v in [metadata.value1,
                  metadata.value2,
                  metadata.value3,
                  metadata.value4,
                  metadata.value5 ]:
            if v:
                dataStrings.append(v.name)
            else:
                break
        if metadata.photo_date:
            dataStrings.append(str(metadata.photo_date))

        return ' '.join(dataStrings)

    def get_location_value_str_list(self):
        """
        Takes an Image object.
        Returns its location values as a list of strings:
        ['Shore3', 'Reef 5', 'Loc10']
        """

        valueList = []
        metadata = self.metadata

        for valueIndex, valueClass in [
                ('value1', Value1),
                ('value2', Value2),
                ('value3', Value3),
                ('value4', Value4),
                ('value5', Value5)
        ]:
            valueObj = getattr(metadata, valueIndex)
            if valueObj:
                valueList.append(valueObj.name)
            else:
                break

        return valueList

    def point_gen_method_display(self):
        """
        Display the point generation method in templates.
        Usage: {{ myimage.point_gen_method_display }}
        """
        return PointGen.db_to_readable_format(self.point_generation_method)
    

class Point(models.Model):
    row = models.IntegerField()
    column = models.IntegerField()
    point_number = models.IntegerField()
    annotation_status = models.CharField(max_length=1, blank=True)
    image = models.ForeignKey(Image)



# General utility methods that involve model classes.
# If you can find a better place for these methods, feel free to move them.

def get_location_value_objs(source, valueList, createNewValues=False):
    """
    Takes a list of values as strings:
    ['Shore3', 'Reef 5', 'Loc10']
    Returns a dict of Value objects:
    {'value1': <Value1 object: 'Shore3'>, 'value2': <Value2 object: 'Reef 5'>, ...}

    If the database doesn't have a Value object of the desired name:
    - If createNewValues is True, then the required Value object is
     created and inserted into the DB.
    - If createNewValues is False, then this method returns False.
    """
    valueNameGen = (v for v in valueList)
    valueDict = dict()

    for valueIndex , valueClass in [
            ('value1', Value1),
            ('value2', Value2),
            ('value3', Value3),
            ('value4', Value4),
            ('value5', Value5)
    ]:
        try:
            valueName = valueNameGen.next()
        except StopIteration:
            # That's all the values the valueList had
            break
        else:
            if createNewValues:
                valueDict[valueIndex], created = valueClass.objects.get_or_create(source=source, name=valueName)
            else:
                try:
                    valueDict[valueIndex] = valueClass.objects.get(source=source, name=valueName)
                except valueClass.DoesNotExist:
                    # Value object not found
                    return False

    # All value objects were found/created
    return valueDict

def find_dupe_image(source, values=None, year=None, **kwargs):
    """
    Sees if the given source already has an image with the given arguments.
    """

    # Get Value objects of the value names given in "values".
    valueObjDict = get_location_value_objs(source, values, createNewValues=False)

    if not valueObjDict:
        # One or more of the values weren't found; no dupe image in DB.
        return False

    # Get all the metadata objects in the DB with these location values and year
    metaMatches = Metadata.objects.filter(photo_date__year=year, **valueObjDict)

    # Get the images from our source that have this metadata.
    imageMatches = Image.objects.filter(source=source, metadata__in=metaMatches)

    if len(imageMatches) > 1:
        raise ValueError("Something's not right - this set of metadata has multiple image matches.")
    elif len(imageMatches) == 1:
        return imageMatches[0]
    else:
        return False
