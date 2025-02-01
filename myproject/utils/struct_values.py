from django.template.defaultfilters import filesizeformat
from wagtail import blocks


class LinkStructValue(blocks.StructValue):
    def get_url(self) -> str:
        if link := self.get("link"):
            return link

        if page := self.get("page"):
            return page.url

        if document := self.get("document"):
            return document.url

        return ""

    def get_title(self) -> str:
        if title := self.get("title"):
            return title

        if page := self.get("page"):
            page = page.specific
            # Safely try to get listing_title; fall back to title if it doesn't exist.
            return getattr(page, 'listing_title', None) or page.title

        if document := self.get("document"):
            return document.title

        return ""

    def get_link_type(self) -> str:
        if self.get("page"):
            return "internal"
        if self.get("document"):
            return "document"
        return "external"

    def get_file_size(self) -> str:
        if document := self.get("document"):
            return filesizeformat(document.file.size)
        return ""

    def get_extension_type(self) -> str:
        if document := self.get("document"):
            return document.file_extension.upper()
        return ""


class CardStructValue(blocks.StructValue):
    def get_image(self):
        """
        Returns a list of images.
        If an image field is provided, it will be returned (wrapped in a list if needed).
        Otherwise, if a link is provided, it will try to retrieve the linked page’s listing_image.
        If nothing is found, an empty list is returned.
        """
        images = []
        image_field = self.get("image")
        if image_field:
            # If the image field contains multiple images, assume it's iterable.
            if isinstance(image_field, list):
                images.extend(image_field)
            else:
                images.append(image_field)

        # If no images were provided via the 'image' field, check the link.
        if not images:
            link = self.get("link")
            if link:
                # If link is a list, iterate over each link.
                if isinstance(link, list):
                    for l in link:
                        page = l.value.get("page")
                        if page:
                            listing_image = getattr(page.specific, 'listing_image', None)
                            if listing_image:
                                if isinstance(listing_image, list):
                                    images.extend(listing_image)
                                else:
                                    images.append(listing_image)
                else:
                    page = link.value.get("page")
                    if page:
                        listing_image = getattr(page.specific, 'listing_image', None)
                        if listing_image:
                            if isinstance(listing_image, list):
                                images.extend(listing_image)
                            else:
                                images.append(listing_image)
        return images

    def get_description(self):
        if description := self.get("description"):
            return description

        if link := self.get("link"):
            # For description, we assume a single link (use the first one if multiple).
            page = link[0].value.get("page") if isinstance(link, list) else link.value.get("page")
            if page:
                page = page.specific
                return page.listing_summary or page.plain_introduction

        return ""
