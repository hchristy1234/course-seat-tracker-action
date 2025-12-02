from bs4 import BeautifulSoup
import json
from courses.base_course import BaseCourse

class PHYSICS_7B(BaseCourse):
    """
    Different than other implementations, this class aims to find total open seats for the
    lecture section of PHYSICS 7B. Aims to find total open seat > 0;
    """
    def __init__(self):
        super().__init__("https://classes.berkeley.edu/content/2026-spring-physics-7b-001-lec-001")

    def parse_html(self, html):
        soup = BeautifulSoup(html, 'html.parser')

        # 1) New structure: enrollment info is in the Drupal settings JSON
        settings_tag = soup.find("script", attrs={"data-drupal-selector": "drupal-settings-json"})
        if settings_tag and settings_tag.string:
            try:
                settings = json.loads(settings_tag.string)
                enrollment = settings.get("ucb", {}).get("enrollment", {})
                if enrollment:
                    # Keep using extract_data so calculate_total_open_seats still works
                    return self.extract_data(enrollment)
            except json.JSONDecodeError:
                pass  # fall through to other strategies

        # 2) Old structure (backwards compatibility): look for data-enrollment attr
        data_element = soup.find(attrs={'data-enrollment': True})
        if data_element:
            try:
                enrollment = json.loads(data_element['data-enrollment'])
                return self.extract_data(enrollment)
            except json.JSONDecodeError:
                pass

        # 3) Fallback: scrape the visible "Total Open Seats" number from the page
        open_seats_span = soup.select_one("section.current-enrollment .top span")
        if open_seats_span:
            try:
                total_open_seats = int(open_seats_span.get_text(strip=True))
                available = total_open_seats > 0
                message = f"PHYSICS 7B has {total_open_seats} seats opened!"
                return available, message
            except ValueError:
                pass

        # If we get here, we really couldn't find anything useful
        raise RuntimeError("Could not find enrollment information on the page.")

    def extract_data(self, enrollment_data):
        """
        enrollment_data is a dict like settings['ucb']['enrollment'] OR
        the old data-enrollment JSON converted to a dict.
        """
        # New pages: entire enrollment dict has 'available' and 'history'
        if 'available' in enrollment_data:
            available_obj = enrollment_data['available']
        else:
            # Old pages might already give us the 'available' object directly
            available_obj = enrollment_data

        total_open_seats = self.calculate_total_open_seats(available_obj)
        available = total_open_seats > 0
        message = f"PHYSICS 7B has {total_open_seats} seats opened!"
        return available, message

    @staticmethod
    def calculate_total_open_seats(available):
        """Algorithm to calculate total open seats for UC Berkeley's courses

        Note: it's not a simply max_enroll - enrolled_count
        Below code refers to:
        https://classes.berkeley.edu/sites/default/files/js/js_wkZa4u4BCnSi4JXgkE3Om2OjgDKSaG35ZwAKoHBOzqI.js

        >>> available = {
        ...        'combination': {
        ...            'maxEnrollCombinedSections': 90,
        ...            'enrolledCountCombinedSections': 118
        ...        },
        ...        'enrollmentStatus': {
        ...            'maxEnroll': 74,
        ...            'enrolledCount': 72
        ...        }}
        >>> CS160.calculate_total_open_seats(available)
        0
        """
        if 'combination' in available:
            combined_open_seats = available['combination']['maxEnrollCombinedSections'] - available['combination']['enrolledCountCombinedSections']
            per_class_open_seats = available['enrollmentStatus']['maxEnroll'] - available['enrollmentStatus']['enrolledCount']
            value = min(combined_open_seats, per_class_open_seats)
            return max(value, 0)
        else:
            return max(available['enrollmentStatus']['maxEnroll'] - available['enrollmentStatus']['enrolledCount'], 0)
