from django.db import models
from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel
from wagtail.search import index
from myproject.utils.models import BasePage

class RentalTrendsPage(BasePage):
    """
    A Wagtail page that displays rental trends (using your CSV data and interactive chart).
    Includes an intro (CharField) and a FAQ section (RichTextField).
    """
    # List of NYC neighborhoods for filtering
    NEIGHBORHOODS = [
        'Manhattan',
        'Brooklyn',
        'Queens',
        'Bronx',
        'Staten Island',
        'NYC',
        'All Downtown',
        'All Midtown',
        'All Upper East Side',
        'All Upper Manhattan',
        'All Upper West Side',
        'Astoria',
        'Auburndale',
        'Bath Beach',
        'Battery Park City',
        'Bay Ridge',
        'Baychester',
        'Bayside',
        'Bedford Park',
        'Bedford-Stuyvesant',
        'Bellerose',
        'Belmont',
        'Bensonhurst',
        'Bergen Beach',
        'Boerum Hill',
        'Borough Park',
        'Briarwood',
        'Brighton Beach',
        'Bronxwood',
        'Brooklyn Heights',
        'Brookville',
        'Brownsville',
        'Bushwick',
        'Cambria Heights',
        'Canarsie',
        'Carroll Gardens',
        'Castle Hill',
        'Central Harlem',
        'Central Park South',
        'Central Queens',
        'Chelsea',
        'Chinatown',
        'City Island',
        'Civic Center',
        'Clearview',
        'Clinton Hill',
        'Co-op City',
        'Cobble Hill',
        'College Point',
        'Columbia St Waterfront District',
        'Concourse',
        'Concourse Village',
        'Corona',
        'Crown Heights',
        'Cypress Hills',
        'DUMBO',
        'Ditmars-Steinway',
        'Downtown Brooklyn',
        'Dyker Heights',
        'East Elmhurst',
        'East Flatbush',
        'East Harlem',
        'East New York',
        'East Village',
        'Eastchester',
        'Elmhurst',
        'Edenwald',
        'Edgemere',
        'Far Rockaway',
        'Financial District',
        'Flatbush',
        'Flatiron',
        'Flatlands',
        'Flushing',
        'Forest Hills',
        'Fort Greene',
        'Fresh Meadows',
        'Glen Oaks',
        'Glendale',
        'Gowanus',
        'Gramercy Park',
        'Gravesend',
        'Greenwich Village',
        'Hamilton Heights',
        'Harlem',
        'Hell\'s Kitchen',
        'Highland Park',
        'Hollis',
        'Howard Beach',
        'Hudson Heights',
        'Inwood',
        'Jackson Heights',
        'Jamaica',
        'Jamaica Estates',
        'Jamaica Hills',
        'Kensington',
        'Kew Gardens',
        'Kew Gardens Hills',
        'Kingsbridge',
        'Kips Bay',
        'Laurelton',
        'Little Italy',
        'Little Neck',
        'Long Island City',
        'Lower East Side',
        'Manhattan Valley',
        'Marble Hill',
        'Marine Park',
        'Maspeth',
        'Melrose',
        'Middle Village',
        'Midtown East',
        'Midtown West',
        'Midwood',
        'Mill Basin',
        'Morris Heights',
        'Morris Park',
        'Morningside Heights',
        'Mott Haven',
        'Murray Hill',
        'Navy Yard',
        'New Dorp',
        'NoHo',
        'NoLita',
        'North Riverdale',
        'Norwood',
        'Ocean Hill',
        'Ocean Parkway',
        'Olinville',
        'Ozone Park',
        'Park Slope',
        'Parkchester',
        'Pelham Bay',
        'Pelham Gardens',
        'Port Morris',
        'Prospect Heights',
        'Prospect Lefferts Gardens',
        'Prospect Park South',
        'Queens Village',
        'Queensboro Hill',
        'Red Hook',
        'Rego Park',
        'Richmond Hill',
        'Ridgewood',
        'Riverdale',
        'Rockaway Beach',
        'Roosevelt Island',
        'Rosedale',
        'Rossville',
        'Schuylerville',
        'Sheepshead Bay',
        'SoHo',
        'South Beach',
        'South Jamaica',
        'South Ozone Park',
        'South Richmond Hill',
        'South Slope',
        'Springfield Gardens',
        'St. Albans',
        'St. George',
        'Stapleton',
        'Stuyvesant Heights',
        'Stuyvesant Town',
        'Sunnyside',
        'Sunset Park',
        'Theater District',
        'Throgs Neck',
        'Todt Hill',
        'Tompkinsville',
        'Tribeca',
        'Two Bridges',
        'University Heights',
        'Upper East Side',
        'Upper West Side',
        'Van Nest',
        'Vinegar Hill',
        'Washington Heights',
        'West Brighton',
        'West Farms',
        'West Village',
        'Westchester Square',
        'Whitestone',
        'Williamsbridge',
        'Williamsburg',
        'Windsor Terrace',
        'Woodhaven',
        'Woodlawn',
        'Woodside'
    ]

    template = "pages/rental_trends_page.html"

    intro = models.CharField(
        max_length=255,
        blank=True,
        help_text='Intro text for the page.'
    )

    body = RichTextField(
        blank=True,
        help_text='Main content for the page.'
    )

    how_to_use = RichTextField(
        blank=True,
        help_text='Instructions on how to use the rental trends tool.'
    )

    data_faqs = RichTextField(
        blank=True,
        help_text='Frequently asked questions about the rental data.'
    )

    content_panels = BasePage.content_panels + [
        FieldPanel('intro'),
        FieldPanel('body'),
        FieldPanel('how_to_use'),
        FieldPanel('data_faqs'),
    ]

    search_fields = BasePage.search_fields + [
        index.SearchField('intro'),
        index.SearchField('body'),
        index.SearchField('how_to_use'),
        index.SearchField('data_faqs'),
    ]

    parent_page_types = ['home.HomePage']
    subpage_types = []

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context['neighborhoods'] = self.NEIGHBORHOODS
        return context

    class Meta:
        verbose_name = "Rental Trends Page"
        verbose_name_plural = "Rental Trends Pages" 