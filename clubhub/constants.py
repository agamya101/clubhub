"""Enumerations — mirror the CHECK constraints in database/schema.sql."""

CLUB_CATEGORIES = ["Technical", "Cultural", "Sports", "Literary", "Social", "Academic"]
CLUB_STATUSES = ["Active", "Inactive"]
BRANCHES = ["CSE", "IT", "ECE", "EE", "ME", "CE", "BT", "MAC", "CSAI", "CSDS"]
DESIGNATIONS = ["Professor", "Associate Professor", "Assistant Professor", "Lecturer"]
MEMBERSHIP_ROLES = ["President", "Vice President", "Secretary", "Treasurer", "Core Member", "Member"]
EVENT_TYPES = ["Workshop", "Webinar", "Hackathon", "Competition", "Session", "Cultural", "Sports", "Meetup"]
EVENT_STATUSES = ["Upcoming", "Ongoing", "Completed", "Cancelled"]
FUNDING_SOURCES = ["College Grant", "Sponsorship", "Membership Fees", "Event Revenue", "Alumni Donation", "Other"]
ASSET_TYPES = ["Electronics", "Instrument", "Furniture", "Sports Gear", "Costume", "Stationery", "Other"]
ASSET_CONDITIONS = ["New", "Good", "Fair", "Needs Repair", "Retired"]
DOC_TYPES = ["Constitution", "Minutes", "Budget", "Report", "Media", "Form", "Other"]
DOC_VISIBILITY = ["Public", "Members", "Private"]
ANNOUNCEMENT_PRIORITY = ["Normal", "Alert"]
ART_FORMS = ["Dance", "Music", "Drama", "Fine Arts", "Fashion", "Photography", "Film"]
ACCOUNT_ROLES = ["Admin", "Student", "Faculty"]

# Which subtype table (if any) each Club.category maps to.
CLUB_SUBTYPE = {"Technical": "Technical_Club", "Cultural": "Cultural_Club", "Sports": "Sports_Club"}
