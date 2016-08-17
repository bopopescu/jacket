import pbr.version

from jacket.i18n import _LE

JACKET_VENDOR = "OpenStack Foundation"
JACKET_PRODUCT = "OpenStack Jacket"
JACKET_PACKAGE = None  # OS distro package version suffix

loaded = False
version_info = pbr.version.VersionInfo('jacket')
version_string = version_info.version_string


def _load_config():
    # Don't load in global context, since we can't assume
    # these modules are accessible when distutils uses
    # this module
    from six.moves import configparser

    from oslo_config import cfg

    import logging

    global loaded, NOVA_VENDOR, NOVA_PRODUCT, NOVA_PACKAGE
    if loaded:
        return

    loaded = True

    cfgfile = cfg.CONF.find_file("release")
    if cfgfile is None:
        return

    try:
        cfg = configparser.RawConfigParser()
        cfg.read(cfgfile)

        if cfg.has_option("Jacket", "vendor"):
            JACKET_VENDOR = cfg.get("Jacket", "vendor")

        if cfg.has_option("Jacket", "product"):
            JACKET_PRODUCT = cfg.get("Jacket", "product")

        if cfg.has_option("Jacket", "package"):
            JACKET_PACKAGE = cfg.get("Jacket", "package")
    except Exception as ex:
        LOG = logging.getLogger(__name__)
        LOG.error(_LE("Failed to load %(cfgfile)s: %(ex)s"),
                  {'cfgfile': cfgfile, 'ex': ex})


def vendor_string():
    _load_config()

    return JACKET_VENDOR


def product_string():
    _load_config()

    return JACKET_PRODUCT


def package_string():
    _load_config()

    return JACKET_PACKAGE


def version_string_with_package():
    if package_string() is None:
        return version_info.version_string()
    else:
        return "%s-%s" % (version_info.version_string(), package_string())
