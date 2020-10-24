import enum
from django.test import RequestFactory, TestCase
from django.forms.models import model_to_dict
from datetime import datetime
from unittest import mock
from .models import Restaurant, InspectionRecords
from .views import get_inspection_info, get_landing_page
from .utils import (
    merge_yelp_info,
    get_restaurant_info_yelp,
    get_restaurant_reviews_yelp,
    query_yelp,
    get_latest_inspection_record,
)

# from getinspection import (
#     clean_inspection_data,
#     match_on_yelp,
#     save_restaurants,
#     save_inspections,
# )
# import pandas as pd
import json


# from pandas.util.testing import assert_frame_equal


def create_restaurant(restaurant_name, business_address, postcode, business_id):
    return Restaurant.objects.create(
        restaurant_name=restaurant_name,
        business_address=business_address,
        postcode=postcode,
        business_id=business_id,
    )


def create_inspection_records(
        restaurant_inspection_id,
        restaurant_name,
        postcode,
        business_address,
        is_roadway_compliant,
        skipped_reason,
        inspected_on,
):
    return InspectionRecords.objects.create(
        restaurant_inspection_id=restaurant_inspection_id,
        restaurant_name=restaurant_name,
        postcode=postcode,
        business_address=business_address,
        is_roadway_compliant=is_roadway_compliant,
        skipped_reason=skipped_reason,
        inspected_on=inspected_on,
    )


# class Compliance(enum.Enum):
#     no = "Non-Compliant"
#     yes = "Compliant"
#     skipped = "Skipped Inspection"


class MockResponse:
    def __init__(self, content, status_code):
        self.content = content
        self.status_code = status_code

    def content(self):
        return self.content


class ModelTests(TestCase):
    def test_create_restaurant(self):
        restaurant = create_restaurant(
            restaurant_name="Gary Danko",
            business_address="800 N Point St",
            postcode="94109",
            business_id="WavvLdfdP6g8aZTtbBQHTw",
        )
        self.assertIsNotNone(restaurant)
        self.assertEqual(restaurant.restaurant_name, "Gary Danko")
        self.assertEqual(restaurant.business_address, "800 N Point St")
        self.assertEqual(restaurant.postcode, "94109")
        self.assertEqual(restaurant.business_id, "WavvLdfdP6g8aZTtbBQHTw")
        self.assertEqual(
            str(restaurant), "1 Gary Danko 800 N Point St 94109 WavvLdfdP6g8aZTtbBQHTw"
        )

    def test_create_inspection_records(self):
        inspection_record = create_inspection_records(
            restaurant_inspection_id="27555",
            restaurant_name="blah blah",
            postcode="11101",
            business_address="somewhere in LIC",
            is_roadway_compliant="Compliant",
            skipped_reason="Nan",
            inspected_on=datetime(2020, 10, 24, 17, 36),
        )
        self.assertIsNotNone(inspection_record)
        self.assertEqual(inspection_record.restaurant_inspection_id, "27555")
        self.assertEqual(inspection_record.restaurant_name, "blah blah")
        self.assertEqual(inspection_record.postcode, "11101")
        self.assertEqual(inspection_record.business_address, "somewhere in LIC")
        self.assertEqual(inspection_record.is_roadway_compliant, "Compliant")
        self.assertEqual(inspection_record.skipped_reason, "Nan")
        self.assertEqual(inspection_record.inspected_on, datetime(2020, 10, 24, 17, 36))
        self.assertEqual(
            str(inspection_record), "27555 blah blah Compliant Nan 2020-10-24 17:36:00 "
                                    "11101 somewhere in LIC"
        )


class InspectionRecordsViewTests(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        self.restaurant = create_restaurant(
            restaurant_name="Tacos El Paisa",
            business_address="1548 St. Nicholas btw West 187th street and west 188th "
                             "street, Manhattan, NY",
            postcode="10040",
            business_id="16",
        )
        self.inspection_records = create_inspection_records(
            restaurant_inspection_id="24111",
            restaurant_name="Tacos El Paisa",
            postcode="10040",
            business_address="1548 St. Nicholas btw West 187th street "
                             "and west 188th "
                             "street, Manhattan, NY",
            is_roadway_compliant="Compliance",
            skipped_reason="No Seating",
            inspected_on=datetime(2020, 10, 21, 12, 30, 30),
        )

    def test_get_valid_restaurant_inspections(self):
        request = self.factory.get("restaurant:inspection_history")
        request.restaurant = self.restaurant
        response = get_inspection_info(request, self.restaurant.id)
        self.assertEqual(response.status_code, 200)

    def test_get_invalid_restaurant_inspections(self):
        request = self.factory.get("restaurant:inspection_history")
        request.restaurant = self.restaurant
        self.restaurant.id = -1
        response = get_inspection_info(request, self.restaurant.id)
        self.assertEqual(response.status_code, 404)


class RestaurantViewTests(TestCase):
    """ Test Restaurant Views """
    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        self.restaurant = create_restaurant(
            restaurant_name="Tacos El Paisa",
            business_address="1548 St. Nicholas btw West 187th street and west 188th "
                             "street, Manhattan, NY",
            postcode="10040",
            business_id="16",
        )
        self.inspection_records = create_inspection_records(
            restaurant_inspection_id="24111",
            restaurant_name="Tacos El Paisa",
            postcode="10040",
            business_address="1548 St. Nicholas btw West 187th street "
                             "and west 188th "
                             "street, Manhattan, NY",
            is_roadway_compliant="Compliance",
            skipped_reason="No Seating",
            inspected_on=datetime(2020, 10, 21, 12, 30, 30),
        )


    def test_valid_get_landing_page(self):
        # restaurant_dict = model_to_dict(self.restaurant)
        # restaurant_dict['yelp_info'] = None
        # restaurant_dict['latest_record'] = self.inspection_records
        # restaurant_list = [restaurant_dict]
        request = self.factory.get("restaurant:browse")
        response = get_landing_page(request, 6)
        self.assertEqual(response.status_code, 200)


class RestaurantUtilsTests(TestCase):

    def test_merge_yelp_info(self):
        restaurant_info = MockResponse(
            json.dumps(
                {
                    "id": "WavvLdfdP6g8aZTtbBQHTw",
                    "name": "Gary Danko",
                    "phone": "+14157492060",
                    "display_phone": "(415) 749-2060",
                    "review_count": 5296,
                    "rating": 4.5,
                    "price": "$$$$",
                }
            ),
            200,
        )
        restaurant_reviews = MockResponse(
            json.dumps(
                {
                    "reviews": [
                        {
                            "id": "xAG4O7l-t1ubbwVAlPnDKg",
                            "rating": 5,
                            "text": "Went back again to this place since the last "
                                    "time i visited the bay area 5 "
                                    "months ago, and nothing has changed. Still the "
                                    "sketchy Mission, "
                                    "Still the cashier...",
                            "time_created": "2016-08-29 00:41:13",
                        },
                        {
                            "id": "1JNmYjJXr9ZbsfZUAgkeXQ",
                            "rating": 4,
                            "text": 'The "restaurant" is inside a small deli so there '
                                    "is no sit down area. Just grab "
                                    "and go.\n\nInside, they sell individually "
                                    "packaged ingredients so that you "
                                    "can...",
                            "time_created": "2016-09-28 08:55:29",
                        },
                        {
                            "id": "SIoiwwVRH6R2s2ipFfs4Ww",
                            "rating": 4,
                            "text": "Dear Mission District,\n\nI miss you and your "
                                    "many delicious late night food "
                                    "establishments and vibrant atmosphere.  I miss "
                                    "the way you sound and smell on "
                                    "a...",
                            "time_created": "2016-08-10 07:56:44",
                        },
                    ],
                    "total": 3,
                    "possible_languages": ["en"],
                }
            ),
            200,
        )
        self.assertEqual(
            merge_yelp_info(restaurant_info, restaurant_reviews),
            {
                "info": json.loads(restaurant_info.content),
                "reviews": json.loads(restaurant_reviews.content),
            },
        )

    def test_get_restaurant_info_yelp(self):
        business_id = "WavvLdfdP6g8aZTtbBQHTw"
        response = get_restaurant_info_yelp(business_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["id"], business_id)

    def test_get_restaurant_reviews_yelp(self):
        business_id = "WavvLdfdP6g8aZTtbBQHTw"
        response = get_restaurant_reviews_yelp(business_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual("reviews" in data, True)

    @mock.patch("restaurant.utils.get_restaurant_info_yelp")
    @mock.patch("restaurant.utils.get_restaurant_reviews_yelp")
    def mock_query_yelp(
            self, mock_get_restaurant_info_yelp, mock_get_restaurant_reviews_yelp
    ):
        business_id = "WavvLdfdP6g8aZTtbBQHTw"
        mock_get_restaurant_info_yelp.return_value = MockResponse(
            {"id": business_id}, 200
        )
        mock_get_restaurant_reviews_yelp.return_value = MockResponse(
            {"reviews": 1}, 200
        )
        data = query_yelp(business_id)
        self.assertIsNotNone(data)
        self.assertEqual(data, {"info": {"id": business_id}, "reviews": {"reviews": 1}})

    # @mock.patch("restaurant.models.Restaurant.objects.all")
    # @mock.patch("restaurant.utils.get_latest_inspection_record")
    # def test_get_restaurant_list(self,
    #                              mock_objects,
    #                              mock_get_latest_inspection_record):
    #     mock_objects.return_value = [
    #         create_restaurant('Gary Danko',
    #                           '800 N Point St',
    #                           '94109',
    #                           "WavvLdfdP6g8aZTtbBQHTw")]
    #     print(mock_objects.return_value[0:1])
    #     #mock_get_latest_inspection_record.return_value = model_to_dict(
    #     # create_inspection_records('11157',
    #     # 'Tacos El Paisa',
    #     # '10040',
    #     # '1548 St. Nicholas btw West 187th street and west 188th street,
    #     # Manhattan, NY',
    #     # Compliance.skipped,
    #     # 'No Seating',
    #     # '2020-07-16 18:09:42')
    #     # )
    #     # #get_restaurant_list(0, 1) TODO
    #     pass


class IntegratedInspectionRestaurantsTests(TestCase):
    """ Test Restaurant Views """

    def test_valid_get_latest_inspections(self):
        restaurant = create_restaurant(
            restaurant_name="Tacos El Paisa",
            business_address="1548 St. Nicholas btw West 187th street and west 188th "
                             "street, Manhattan, NY",
            postcode="10040",
            business_id="16",
        )
        InspectionRecords.objects.create(
            restaurant_inspection_id="24111",
            restaurant_name="Tacos El Paisa",
            postcode="10040",
            business_address="1548 St. Nicholas btw West 187th street and west 188th "
                             "street, Manhattan, NY",
            is_roadway_compliant="Compliant",
            skipped_reason="No Seating",
            inspected_on=datetime(2020, 10, 21, 12, 30, 30),
        )
        target_inspection = InspectionRecords.objects.create(
            restaurant_inspection_id="24112",
            restaurant_name="Tacos El Paisa",
            postcode="10040",
            business_address="1548 St. Nicholas btw West 187th street and west 188th "
                             "street, Manhattan, NY",
            is_roadway_compliant="Non-Compliant",
            skipped_reason="No Seating",
            inspected_on=datetime(2020, 10, 22, 12, 30, 30),
        )

        latest_inspection = get_latest_inspection_record(
            restaurant.restaurant_name,
            restaurant.business_address,
            restaurant.postcode,
        )
        self.assertEqual(latest_inspection, model_to_dict(target_inspection))

    def test_invalid_get_inspection_info(self):
        restaurant = create_restaurant(
            restaurant_name="Tacos El Paisa",
            business_address="1548 St. Nicholas btw West 187th street and west 188th "
                             "street, Manhattan, NY",
            postcode="10040",
            business_id="16",
        )
        latest_inspection = get_latest_inspection_record(
            restaurant.restaurant_name,
            restaurant.business_address,
            restaurant.postcode,
        )
        self.assertEqual(latest_inspection, None)


class GetInspectionDataTests(TestCase):
    """ Test Get/Save Inspection data Script"""

    # def test_clean_inspection_data(self):
    #     result = [
    #         {
    #             "borough": "Manhattan",
    #             "restaurantname": "AJISEN RAMEN",
    #             "seatingchoice": "both",
    #             # "legalbusinessname": "AJISEN RAMEN CHELSEA INC.",
    #             "businessaddress": "136 WEST 28TH STREET",
    #             "restaurantinspectionid": "25808",
    #             "isroadwaycompliant": "Skipped Inspection",
    #             "skippedreason": "No Seating",
    #             "inspectedon": "2020-10-19T10:57:21.000",
    #             "agencycode": "DOT",
    #             "postcode": "10001",
    #             "latitude": "40.746520",
    #             "longitude": "-73.991678",
    #             "communityboard": "5",
    #             "councildistrict": "3",
    #             "censustract": "95",
    #             "bin": "1015092",
    #             "bbl": "1008030060",
    #             "nta": "Midtown-Midtown South",
    #         }
    #     ]
    #
    #     results_df = pd.DataFrame.from_records(result)
    #     restaurant = [
    #         {
    #             "restaurantname": "AJISEN RAMEN",
    #             # "legalbusinessname": "AJISEN RAMEN CHELSEA INC.",
    #             "businessaddress": "136 WEST 28TH STREET",
    #             "postcode": "10001",
    #         }
    #     ]
    #     r_df = pd.DataFrame.from_records(restaurant)
    #     restaurant_df, inspection_df = clean_inspection_data(results_df)
    #
    #     assert_frame_equal(restaurant_df, r_df)

    # def test_match_on_yelp(self):
    #     restaurant_name = "AJISEN RAMEN"
    #     restaurant_location = "136 WEST 28TH STREET"
    #     b_id = "2SMaAUcbNjW7vSwdg38P2Q"
    #     response = json.loads(match_on_yelp(restaurant_name, restaurant_location))
    #
    #     self.assertEqual(response["businesses"][0]["id"], b_id)

    # def test_save_restaurants(self):
    #     restaurant = [
    #         {
    #             "restaurantname": "AJISEN RAMEN",
    #             # "legalbusinessname": "AJISEN RAMEN CHELSEA INC.",
    #             "businessaddress": "136 WEST 28TH STREET",
    #             "postcode": "10001",
    #         }
    #     ]
    #     r_df = pd.DataFrame.from_records(restaurant)
    #
    #     save_restaurants(r_df)
    #
    #     return True

    # @mock.patch("getinspection.match_on_yelp")
    # def test_save_restaurants_catch(self, mock_match_on_yelp):
    #     restaurant = [
    #         {
    #             "restaurantname": "AJISEN RAMEN",
    #             # "legalbusinessname": "AJISEN RAMEN CHELSEA INC.",
    #             "businessaddress": "136 WEST 28TH STREET",
    #             "postcode": "10001",
    #         }
    #     ]
    #     r_df = pd.DataFrame.from_records(restaurant)
    #
    #     # business_id = "2SMaAUcbNjW7vSwdg38P2Q"
    #     mock_match_on_yelp.return_value = MockResponse(
    #         {
    #             "businesses": [
    #                 {
    #                     "id": "2SMaAUcbNjW7vSwdg38P2Q",
    #                     "alias": "ajisen-ramen-new-york-2",
    #                     "name": "Ajisen Ramen",
    #                     "coordinates": {"latitude": 40.74661, "longitude": -73.9921},
    #                     "location": {
    #                         "address1": "136 W 28th St",
    #                         "address2": None,
    #                         "address3": "",
    #                         "city": "New York",
    #                         "zip_code": "10001",
    #                         "country": "US",
    #                         "state": "NY",
    #                         "display_address":
    #                         ["136 W 28th St", "New York, NY 10001"],
    #                     },
    #                     "phone": "+16466380888",
    #                     "display_phone": "(646) 638-0888",
    #                 }
    #             ]
    #         },
    #         200,
    #     )
    #
    #     save_restaurants(r_df)
    #
    #     return True

    # def test_save_inspections(self):
    #     inspections = [
    #         {
    #             "restaurantname": "AJISEN RAMEN",
    #             "businessaddress": "136 WEST 28TH STREET",
    #             "restaurantinspectionid": "25808",
    #             "isroadwaycompliant": "Skipped Inspection",
    #             "skippedreason": "No Seating",
    #             "inspectedon": "2020-10-19T10:57:21.000",
    #             "postcode": "10001",
    #         }
    #     ]
    #
    #     in_rec_df = pd.DataFrame.from_records(inspections)
    #
    #     save_inspections(in_rec_df)
    #
    #     return True

    # @mock.patch("getinspection.clean_inspection_data")
    # @mock.patch("getinspection.save_restaurants")
    # @mock.patch("getinspection.save_inspections")
    # @mock.patch("getinspection.get_inspection_data.client.get")

    # def test_get_inspection_data(self,
    #                              mock_clean_inspection_data,
    #                              mock_save_restaurants,
    #                              mock_save_inspections):
    #     inspection1 = InspectionRecords.objects.create(
    #         restaurant_Inspection_ID="24111",
    #         restaurant_name="Tacos El Paisa",
    #         postcode="10040",
    #         business_address="1548 St. Nicholas btw West 187th street and west 188th "
    #                          "street, Manhattan, NY",
    #         is_roadway_compliant="Compliant",
    #         skipped_reason="No Seating",
    #         inspected_on=datetime(2020, 10, 21, 12, 30, 30),
    #     )
    #     inspection2 = InspectionRecords.objects.create(
    #         restaurant_Inspection_ID="24112",
    #         restaurant_name="Tacos El Paisa",
    #         postcode="10040",
    #         business_address="1548 St. Nicholas btw West 187th street and west 188th "
    #                          "street, Manhattan, NY",
    #         is_roadway_compliant="Non-Compliant",
    #         skipped_reason="No Seating",
    #         inspected_on=datetime(2020, 10, 22, 12, 30, 30),
    #     )
    #     # mock_get.return_value = [
    #     #         {
    #     #             "borough": "Manhattan",
    #     #             "restaurantname": "AJISEN RAMEN",
    #     #             "seatingchoice": "both",
    #     #             "legalbusinessname": "AJISEN RAMEN CHELSEA INC.",
    #     #             "businessaddress": "136 WEST 28TH STREET",
    #     #             "restaurantinspectionid": "25808",
    #     #             "isroadwaycompliant": "Skipped Inspection",
    #     #             "skippedreason": "No Seating",
    #     #             "inspectedon": "2020-10-19T10:57:21.000",
    #     #             "agencycode": "DOT",
    #     #             "postcode": "10001",
    #     #             "latitude": "40.746520",
    #     #             "longitude": "-73.991678",
    #     #             "communityboard": "5",
    #     #             "councildistrict": "3",
    #     #             "censustract": "95",
    #     #             "bin": "1015092",
    #     #             "bbl": "1008030060",
    #     #             "nta": "Midtown-Midtown South"
    #     #         }
    #     #     ]
    #     inspections = [
    #         {'restaurantname': 'AJISEN RAMEN',
    #          'businessaddress': '136 WEST 28TH STREET',
    #          'restaurantinspectionid': '25808',
    #          'isroadwaycompliant': 'Skipped Inspection',
    #          'skippedreason': 'No Seating',
    #          'inspectedon': '2020-10-19T10:57:21.000',
    #          'postcode': '10001'}
    #     ]
    #     in_rec_df = pd.DataFrame.from_records(inspections)
    #
    #     restaurant = [
    #         {'restaurantname': 'AJISEN RAMEN',
    #          'legalbusinessname': 'AJISEN RAMEN CHELSEA INC.',
    #          'businessaddress': '136 WEST 28TH STREET',
    #          'postcode': '10001'}
    #     ]
    #     r_df = pd.DataFrame.from_records(restaurant)
    #
    #     mock_clean_inspection_data.return_value = r_df
    #     mock_save_restaurants = True
    #     mock_save_inspections = True
    #
    #     get_inspection_data()
    #
    #     return True
