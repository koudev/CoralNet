import datetime
from decimal import Decimal
import math, random
from os.path import splitext

# This file contains general utility methods that do NOT directly reference model classes.
# (models.py may use these utility methods, so having this file reference model classes
# would create a circular import dependency.)

class PointGen():
    """
    Utility class for point generation, including:
    - Generating points.
    - Going between human-readable format and DB-friendly encoding
    of the point generation method.

    Examples of the DB-friendly encoding:
    m_80 -> Simple random, 80 points
    t_8_6_4 -> Stratified random, 8x6 cells, 4 points per cell
    u_10_8 -> Uniform grid, 10x8 grid
    i_80 -> Imported, 80 points
    """
    class Types():
        SIMPLE = 'm'
        SIMPLE_VERBOSE = 'Simple Random (Random within the entire annotation area)'
        STRATIFIED = 't'
        STRATIFIED_VERBOSE = 'Stratified Random (Random within a cell of the annotation area)'
        UNIFORM = 'u'
        UNIFORM_VERBOSE = 'Uniform Grid'
        IMPORTED = 'i'
        IMPORTED_VERBOSE = 'Imported (Not generated by CoralNet)'

    @staticmethod
    def args_to_db_format(point_generation_type=None,
                          simple_number_of_points=None,
                          number_of_cell_rows=None,
                          number_of_cell_columns=None,
                          stratified_points_per_cell=None,
                          imported_number_of_points=None):

        if point_generation_type == PointGen.Types.SIMPLE:
            extraArgs = [simple_number_of_points]
        elif point_generation_type == PointGen.Types.STRATIFIED:
            extraArgs = [number_of_cell_rows,
                          number_of_cell_columns,
                          stratified_points_per_cell]
        elif point_generation_type == PointGen.Types.UNIFORM:
            extraArgs = [number_of_cell_rows,
                          number_of_cell_columns]
        elif point_generation_type == PointGen.Types.IMPORTED:
            extraArgs = [imported_number_of_points]
        else:
            raise ValueError("Point generation type is not a known type.")

        for arg in extraArgs:
            if arg is None:
                raise ValueError("Point generation method is missing a required argument.")

        # Make sure we have strings, not ints
        extraArgs = [str(arg) for arg in extraArgs]

        return '_'.join([point_generation_type] + extraArgs)

    @staticmethod
    def args_to_readable_format(point_generation_type=None,
                                simple_number_of_points=None,
                                number_of_cell_rows=None,
                                number_of_cell_columns=None,
                                stratified_points_per_cell=None,
                                imported_number_of_points=None):
        
        if point_generation_type == PointGen.Types.SIMPLE:
            return "Simple random, %s points" % simple_number_of_points
        elif point_generation_type == PointGen.Types.STRATIFIED:
            return "Stratified random, %s rows x %s columns of cells, %s points per cell (total of %s points)" % (
                   number_of_cell_rows, number_of_cell_columns, stratified_points_per_cell,
                   number_of_cell_rows*number_of_cell_columns*stratified_points_per_cell
                )
        elif point_generation_type == PointGen.Types.UNIFORM:
            return "Uniform grid, %s rows x %s columns (total of %s points)" % (
                   number_of_cell_rows, number_of_cell_columns,
                   number_of_cell_rows*number_of_cell_columns
                )
        elif point_generation_type == PointGen.Types.IMPORTED:
            return "Imported, %s points" % imported_number_of_points
        else:
            raise ValueError("Point generation type is not a known type.")

    @staticmethod
    def db_to_args_format(db_format):
        tokens = db_format.split('_')

        if tokens[0] == PointGen.Types.SIMPLE:
            return dict(point_generation_type=tokens[0],
                        simple_number_of_points=int(tokens[1]))

        elif tokens[0] == PointGen.Types.STRATIFIED:
            return dict(point_generation_type=tokens[0],
                        number_of_cell_rows=int(tokens[1]),
                        number_of_cell_columns=int(tokens[2]),
                        stratified_points_per_cell=int(tokens[3]))

        elif tokens[0] == PointGen.Types.UNIFORM:
            return dict(point_generation_type=tokens[0],
                        number_of_cell_rows=int(tokens[1]),
                        number_of_cell_columns=int(tokens[2]))

        elif tokens[0] == PointGen.Types.IMPORTED:
            return dict(point_generation_type=tokens[0],
                        imported_number_of_points=int(tokens[1]))

    @staticmethod
    def db_to_readable_format(db_format):
        return PointGen.args_to_readable_format(**PointGen.db_to_args_format(db_format))

    @staticmethod
    def generate_points(img,
                        point_generation_type=None,
                        simple_number_of_points=None,
                        number_of_cell_rows=None,
                        number_of_cell_columns=None,
                        stratified_points_per_cell=None
    ):
        """
        Generate points for this image. This doesn't actually
        insert anything in the database; it just generates the
        row, column for each point number.

        Returns the points as a list of dicts; each dict
        represents a point, and has keys "row", "column",
        and "point_number".
        """

        points = []

        if point_generation_type == PointGen.Types.SIMPLE:

            simple_random_points = []

            for i in range(simple_number_of_points):
                row = int(math.floor(random.random()*(img.original_height+1)))  # 0 to img.original_height
                column = int(math.floor(random.random()*(img.original_width+1)))  # 0 to img.original_width

                simple_random_points.append({'row': row, 'column': column})

            # For ease of finding consecutive points, impose cell rows and cols, then
            # make consecutive points fill the cells one by one.
            NUM_OF_CELL_ROWS = 5
            NUM_OF_CELL_COLUMNS = 5
            cell = {}
            for r in range(NUM_OF_CELL_ROWS):
                cell[r] = {}
                for c in range(NUM_OF_CELL_COLUMNS):
                    cell[r][c] = []

            for p in simple_random_points:
                r = int(math.floor( (p['row'] * NUM_OF_CELL_ROWS) / (img.original_height+1) ))
                c = int(math.floor( (p['column'] * NUM_OF_CELL_COLUMNS) / (img.original_width+1) ))
                if r >= 5 or c >= 5:
                    print r, c
                cell[r][c].append(p)

            point_num = 1
            for r in range(NUM_OF_CELL_ROWS):
                for c in range(NUM_OF_CELL_COLUMNS):
                    for p in cell[r][c]:

                        points.append(dict(row=p['row'], column=p['column'], point_number=point_num))
                        point_num += 1

        elif point_generation_type == PointGen.Types.STRATIFIED:

            point_num = 1

            for row_num in range(0, number_of_cell_rows):
                row_min = (row_num * img.original_height) / number_of_cell_rows
                row_max = (((row_num+1) * img.original_height) / number_of_cell_rows) - 1

                for col_num in range(0, number_of_cell_columns):
                    col_min = (col_num * img.original_width) / number_of_cell_columns
                    col_max = (((col_num+1) * img.original_width) / number_of_cell_columns) - 1

                    for cell_point_num in range(0, stratified_points_per_cell):
                        row = row_min + int(math.floor(random.random()*(row_max - row_min +1)))  # row_min to row_max
                        column = col_min + int(math.floor(random.random()*(col_max - col_min +1)))  # col_min to col_max

                        points.append(dict(row=row, column=column, point_number=point_num))
                        point_num += 1

        elif point_generation_type == PointGen.Types.UNIFORM:

            point_num = 1

            for row_num in range(0, number_of_cell_rows):
                row_mid = ((row_num+0.5) * img.original_height) / number_of_cell_rows

                for col_num in range(0, number_of_cell_columns):
                    col_mid = ((col_num+0.5) * img.original_width) / number_of_cell_columns

                    points.append(dict(row=row_mid, column=col_mid, point_number=point_num))
                    point_num += 1

        return points


class AnnotationAreaUtils():

    @staticmethod
    def percentage_decimals_to_string(min_x, max_x, min_y, max_y):
        # Handle the case where the field is not filled at all.
        if min_x is None and max_x is None and \
           min_y is None and max_y is None:
            return ''
        
        return ','.join([
            str(min_x), str(max_x), str(min_y), str(max_y)
        ])

    @staticmethod
    def percentage_string_to_decimals(s):
        d = dict()
        d['min_x'], d['max_x'], d['min_y'], d['max_y'] = [Decimal(dec_str) for dec_str in s.split(',')]
        return d

    @staticmethod
    def pixel_integers_to_string(min_x, max_x, min_y, max_y):
        # Handle the case where the field is not filled at all.
        if min_x is None and max_x is None and \
           min_y is None and max_y is None:
            return ''

        return ','.join([
            str(min_x), str(max_x), str(min_y), str(max_y)
        ])

    @staticmethod
    def pixel_string_to_integers(s):
        d = dict()
        d['min_x'], d['max_x'], d['min_y'], d['max_y'] = [int(int_str) for int_str in s.split(',')]
        return d

    @staticmethod
    def percentages_to_pixels(min_x, max_x, min_y, max_y, width, height):
        d = dict()

        # The percentages are Decimals.
        # Decimal / int = Decimal, and Decimal * int = Decimal
        d['min_x'] = (min_x / 100) * width
        d['max_x'] = (max_x / 100) * width
        d['min_y'] = (min_y / 100) * height
        d['max_y'] = (max_y / 100) * height

        for key in d.keys():
            # Convert to integer pixel values.
            # Round up (could just as well round down, need to pick one or the other).
            d[key] = int(math.ceil(d[key]))

            # Corner case
            if d[key] == 0:
                d[key] = 1

        return d

    @staticmethod
    def percentage_string_to_readable_format(s):
        d = AnnotationAreaUtils.percentage_string_to_decimals(s)
        return "X: %s - %s%% / Y: %s - %s%%" % (
            d['min_x'], d['max_x'], d['min_y'], d['max_y']
            )

    @staticmethod
    def pixel_string_to_readable_format(s):
        d = AnnotationAreaUtils.pixel_string_to_integers(s)
        return "X: %s - %s pixels / Y: %s - %s pixels" % (
            d['min_x'], d['max_x'], d['min_y'], d['max_y']
            )

    @staticmethod
    def percentage_string_to_pixels_readable_format(s, width, height):
        percent_d = AnnotationAreaUtils.percentage_string_to_decimals(s)
        pixel_d = AnnotationAreaUtils.percentages_to_pixels(width=width, height=height, **percent_d)
        return "X: %s - %s pixels (%s - %s%%) / Y: %s - %s pixels (%s - %s%%)" % (
            pixel_d['min_x'], pixel_d['max_x'],
            percent_d['min_x'], percent_d['max_x'],
            pixel_d['min_y'], pixel_d['max_y'],
            percent_d['min_y'], percent_d['max_y']
            )


def filename_to_metadata(filename, source):
    """
    Takes an image filename without the extension.

    Returns a dict of the location values, and the photo year, month, and day.
    {'values': ['Shore3', 'Reef 5', 'Loc10'],
     'year': 2007, 'month': 8, 'day': 15}
    """

    metadataDict = dict()

    parseError = ValueError('Could not properly extract metadata from the filename "%s".' % filename)
    dateError = ValueError('Invalid date format or values.')
    numOfKeys = source.num_of_keys()

    # value1_value2_..._YYYY-MM-DD
    tokensFormat = ['value'+str(i) for i in range(1, numOfKeys+1)]
    tokensFormat += ['date']
    numTokensExpected = len(tokensFormat)

    # Make a list of the metadata 'tokens' from the filename
    filenameWithoutExt, extension = splitext(filename)
    tokens = filenameWithoutExt.split('_')

    dataTokens = tokens[:numTokensExpected]
    if len(dataTokens) != numTokensExpected:
        raise parseError

    extraTokens = tokens[numTokensExpected:]
    if len(extraTokens) > 0:
        name = '_'.join(extraTokens) + extension
    else:
        name = filename

    # Encode the filename data into a dictionary: {'value1':'Shore2', 'date':'2008-12-18', ...}
    filenameData = dict(zip(tokensFormat, dataTokens))

    valueList = [filenameData['value'+str(i)] for i in range(1, numOfKeys+1)]
    dateToken = filenameData['date']

    try:
        year, month, day = dateToken.split("-")
    except ValueError:
        raise dateError
    # YYYYMMDD parsing:
#    if len(dateToken) != 8:
#        raise dateError
#    year, month, day = dateToken[:4], dateToken[4:6], dateToken[6:8]

    try:
        datetime.date(int(year), int(month), int(day))
    except ValueError:
        # Either non-integer date params, or date params are
        # out of valid range (e.g. month 13)
        raise dateError

    metadataDict['values'] = valueList

    metadataDict['year'] = year
    metadataDict['month'] = month
    metadataDict['day'] = day

    metadataDict['name'] = name

    return metadataDict


def metadata_to_filename(values=None,
                         year=None, month=None, day=None):
    """
    Takes metadata arguments and returns a filename (without the extension)
    which would generate these arguments.
    """

    dateStr = '-'.join([year, month, day])
    filename = '_'.join(values + [dateStr])

    return filename
