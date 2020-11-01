import pynetbox
import resources


class Netbox(pynetbox.api):
    pass


if __name__ == '__main__':
    import os

    nb = Netbox(os.environ.get('NETBOX_URL'),
                token=os.environ.get('NETBOX_TOKEN'))
