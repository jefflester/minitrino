// Copied from PyData Sphinx Theme docs _static/custom-icons.js
// (No logo or branding references)

// Example: Add custom icons for PyPI and PyData for use in icon_links
window.addEventListener("DOMContentLoaded", () => {
  const faPyPI = {
    prefix: "fa-custom",
    iconName: "fa-pypi",
    icon: [
      24, 24, [], null,
      "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"
    ]
  };
  const faPyData = {
    prefix: "fa-custom",
    iconName: "fa-pydata",
    icon: [
      24, 24, [], null,
      "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm2-13h-4v2h4zm0 4h-4v6h4z"
    ]
  };
  if (window.FontAwesome && window.FontAwesome.library) {
    window.FontAwesome.library.add(faPyPI, faPyData);
  }
});
