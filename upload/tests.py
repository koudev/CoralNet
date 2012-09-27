import os
from django.conf import settings
from django.core.urlresolvers import reverse
from django.forms import forms
from django.utils import simplejson
from images.forms import ImageUploadForm
from images.models import Source, Image
from lib.test_utils import ClientTest, MediaTestComponent


class ImageUploadBaseTest(ClientTest):
    """
    Base test class for the image upload page.

    This is an abstract class of sorts, as it doesn't actually contain
    any test methods.  However, its subclasses have test methods.
    """
    extra_components = [MediaTestComponent]
    fixtures = ['test_users.yaml', 'test_sources_with_different_keys.yaml']
    source_member_roles = [
        ('1 key', 'user2', Source.PermTypes.ADMIN.code),
        ('2 keys', 'user2', Source.PermTypes.ADMIN.code),
        ('5 keys', 'user2', Source.PermTypes.ADMIN.code),
        ]

    def setUp(self):
        super(ImageUploadBaseTest, self).setUp()

        # Default user; individual tests are free to change it
        self.client.login(username='user2', password='secret')

        # Default source; individual tests are free to change it
        self.source_id = Source.objects.get(name='1 key').pk

    def upload_image_test(self, filename,
                          expecting_dupe=False,
                          expected_error=None,
                          **options):
        """
        Upload a single image via the Ajax view.

        (Multi-image upload only takes place on the client side; it's really
        just a series of single-image uploads on the server side. So unit
        testing multi-image upload doesn't make sense unless we can
        test on the client side, with Selenium or something.)

        :param filename: The image file's filepath as a string, relative to
            <settings.SAMPLE_UPLOADABLES_ROOT>/data.
        :param expecting_dupe: True if we expect the image to be a duplicate
            of an existing image, False otherwise.
        :param expected_error: Expected error message, if any.
        :param options: Extra options to include in the Ajax-image-upload
            request.
        :return: The response from sending the Ajax-image-upload request.
            This way, the calling function can do something else with the
            response if it wants to.
        """
        old_source_image_count = Image.objects.filter(source=Source.objects.get(pk=self.source_id)).count()

        sample_uploadable_directory = os.path.join(settings.SAMPLE_UPLOADABLES_ROOT, 'data')

        sample_uploadable_path = os.path.join(sample_uploadable_directory, filename)
        file_to_upload = open(sample_uploadable_path, 'rb')

        post_dict = dict(
            file=file_to_upload,
            specify_metadata='filenames',
            skip_or_replace_duplicates='skip',
            is_uploading_points_or_annotations='off',
            is_uploading_annotations_not_just_points='yes',
            annotation_dict_id='',
        )
        post_dict.update(options)

        response = self.client.post(
            reverse('image_upload_ajax', kwargs={'source_id': self.source_id}),
            post_dict,
        )
        file_to_upload.close()
        response_content = simplejson.loads(response.content)

        self.assertStatusOK(response)

        new_source_image_count = Image.objects.filter(source=Source.objects.get(pk=self.source_id)).count()

        if expected_error:

            self.assertEqual(response_content['status'], 'error')
            self.assertEqual(response_content['message'], expected_error)

            # TODO: Add error output in verbose mode.

            # Error, so nothing was uploaded.
            # The number of images in the source should have stayed the same.
            self.assertEqual(new_source_image_count, old_source_image_count)

        else:

            self.assertEqual(response_content['status'], 'ok')

            if expecting_dupe:
                # TODO: Make sure the image on the server has a correct upload date?
                # (i.e. a datetime greater or equal to a time just before the upload.)

                # We just replaced a duplicate image.
                # The number of images in the source should have stayed the same.
                self.assertEqual(new_source_image_count, old_source_image_count)
            else:
                # We uploaded a new, non-duplicate image.
                # The number of images in the source should have gone up by 1.
                self.assertEqual(new_source_image_count, 1+old_source_image_count)

        return response


class ImageUploadGeneralTest(ImageUploadBaseTest):
    """
    Image upload tests: general.
    """
    def test_valid_png(self):
        """ .png created using the PIL. """
        self.upload_image_test('001_2012-05-01_color-grid-001.png')

    def test_valid_jpg(self):
        """ .jpg created using the PIL. """
        self.upload_image_test('001_2012-05-01_color-grid-001_jpg-valid.jpg')

    # TODO: Test a fairly large upload (at least 50 MB, or whatever
    # the upload limit is when memory is used for temp storage)?


class ImageUploadImageErrorTest(ImageUploadBaseTest):
    """
    Image upload tests: errors related to the image files, such as errors
    about corrupt images, non-images, etc.
    """
    invalid_image_error_msg = ImageUploadForm.base_fields['file'].error_messages['invalid_image']

    def test_unloadable_corrupt_png_1(self):
        """ .png with some bytes swapped around.
        PIL load() would get IOError: broken data stream when reading image file """
        self.upload_image_test(
            '001_2012-05-01_color-grid-001_png-corrupt-unloadable-1.png',
            expected_error=self.invalid_image_error_msg,
        )

    def test_unloadable_corrupt_png_2(self):
        """ .png with some bytes deleted from the end.
        PIL load() would get IndexError: string index out of range """
        self.upload_image_test(
            '001_2012-05-01_color-grid-001_png-corrupt-unloadable-2.png',
            expected_error=self.invalid_image_error_msg,
        )

    def test_unopenable_corrupt_png(self):
        """ .png with some bytes deleted near the beginning.
        PIL open() would get IOError: cannot identify image file """
        self.upload_image_test(
            '001_2012-05-01_color-grid-001_png-corrupt-unopenable.png',
            expected_error=self.invalid_image_error_msg,
        )

    def test_unloadable_corrupt_jpg(self):
        """ .jpg with bytes deleted from the end.
        PIL load() would get IOError: image file is truncated (4 bytes not processed) """
        self.upload_image_test(
            '001_2012-05-01_color-grid-001_jpg-corrupt-unloadable.jpg',
            expected_error=self.invalid_image_error_msg,
        )

    def test_unopenable_corrupt_jpg(self):
        """ .jpg with bytes deleted near the beginning.
        PIL open() would get IOError: cannot identify image file """
        self.upload_image_test(
            '001_2012-05-01_color-grid-001_jpg-corrupt-unopenable.jpg',
            expected_error=self.invalid_image_error_msg,
        )

    def test_non_image(self):
        """ .txt in UTF-8 created using Notepad++.
        NOTE: the filename will have to be valid for an
        equivalent Selenium test."""
        self.upload_image_test(
            'sample_text_file.txt',
            expected_error=self.invalid_image_error_msg,
        )

    def test_empty_file(self):
        """ 0-byte .png.
        NOTE: the filename will have to be valid for an
        equivalent Selenium test."""
        self.upload_image_test(
            'empty.png',
            expected_error=forms.FileField.default_error_messages['empty']
        )

    # TODO: Test uploading a nonexistent file (i.e. filling the file field with
    # a nonexistent filename).  However, this will probably have to be done
    # with a Selenium test.

    def test_no_images_specified(self):
        post_dict = dict(
            file='',
            specify_metadata='filenames',
            skip_or_replace_duplicates='skip',
            is_uploading_points_or_annotations='off',
        )
        response = self.client.post(
            reverse('image_upload_ajax', kwargs={'source_id': self.source_id}),
            post_dict,
        )

        self.assertStatusOK(response)

        # TODO: Check for the appropriate error.