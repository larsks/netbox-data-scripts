import attr
import json
import re
import typing

from attr import attrs, attrib


@attrs(kw_only=True)
class Base:
    _selectors = ('name',)
    _exclude = ()

    slug: str = attrib(None)
    id: int = attrib(None)
    url: str = attrib(None)
    created: str = attrib(None)
    last_updated: str = attrib(None)

    def __attrs_post_init__(self):
        if self.slug is None and self._selectors:
            val = ' '.join((
                str(getattr(self, attrname)).lower()
                for attrname in self._selectors
            ))

            val = re.sub(r'\s+', '-', val)
            val = re.sub(r'[^a-z0-9-]+', '-', val)
            val = re.sub(r'-+', '-', val)
            val = re.sub(r'(^-)|(-$)', '', val)

            self.slug = val

    def to_dict(self):
        return attr.asdict(self,
                           filter=lambda k, v: v is not None and k not in self._exclude)

    def to_json(self):
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data):
        kwargs = {spec.name: data[spec.name]
                  for spec in cls.__attrs_attrs__
                  if spec.name in data}
        return cls(**kwargs)


@attrs(kw_only=True)
class device_type(Base):
    _route = '/api/dcim/device-types/'
    _selectors = ('manufacturer', 'model')

    manufacturer: str = attrib()
    model: str = attrib()
    display_name: str = attrib(None)
    part_number: str = attrib(None)
    u_height: int = attrib(None)
    is_full_depth: bool = attrib(None)
    subdevice_role: str = attrib(None)
    comments: str = attrib(None)


@attrs(kw_only=True)
class device_role(Base):
    _route = '/api/dcim/device-roles/'

    name: str = attrib()
    description: str = attrib(None)


@attrs(kw_only=True)
class manufacturer(Base):
    _route = '/api/dcim/manufacturers/'

    name: str = attrib()
    description: str = attrib(None)

    devicetype_count: int = attrib(None)
    inventoryitem_count: int = attrib(None)
    platform_count: int = attrib(None)


@attrs(kw_only=True)
class site(Base):
    _route = '/api/dcim/sites/'

    name: str = attrib()
    status: str = attrib('active')
    region: int = attrib(None)
    tenant: int = attrib(None)
    facility: str = attrib(None)
    time_zone: str = attrib(None)
    description: str = attrib(None)
    physical_address: str = attrib(None)
    mailing_address: str = attrib(None)
    contact_name: str = attrib(None)
    contact_email: str = attrib(None)
    contact_phone: str = attrib(None)
    comments: str = attrib(None)


@attrs(kw_only=True)
class device_type_ref:
    manufacturer: str = attrib()
    model: str = attrib()


@attrs(kw_only=True)
class device(Base):
    _route = '/api/dcim/devices/'
    _exclude = ('interfaces',)

    name: str = attrib(None)
    display_name: str = attrib(None)
    device_type: device_type_ref = attrib(None)
    device_role: str = attrib(None)
    tenant: str = attrib(None)
    platform: str = attrib(None)
    serial: str = attrib(None)
    asset_tag: str = attrib(None)
    site: str = attrib(None)
    rack: str = attrib(None)
    position: int = attrib(None)
    face: str = attrib(None)
    status: str = attrib(None)
    primary_ip: str = attrib(None)
    primary_ip4: str = attrib(None)
    primary_ip6: str = attrib(None)
    cluster: str = attrib(None)
    comments: str = attrib(None)
    interfaces = attrib(None)

    @classmethod
    def from_ansible_facts(cls, facts,
                           device_role='Server',
                           cluster=None,
                           site=None):
        dt = device_type_ref(
            manufacturer=facts['ansible_system_vendor'],
            model=facts['ansible_product_name'],
        )

        dev = cls(
            name=facts['ansible_fqdn'],
            device_type=dt,
            serial=facts.get('ansible_product_serial'),
            device_role=device_role,
            primary_ip=facts.get('ansible_default_ipv4', {}).get('address'),
            cluster=cluster,
            site=site,
        )
        dev.interfaces = interface_list.from_ansible_facts(dev, facts)

        return dev


@attrs(kw_only=True)
class interface(Base):
    _route = '/api/dcim/interfaces/'
    _selectors = ()

    device: device = attrib(None)
    name: str = attrib(None)
    label: str = attrib(None)
    type: str = attrib('1000base-t')
    enabled: bool = attrib(None)
    mac_address: str = attrib(None)
    mtu: int = attrib(None)
    mgmt_only: bool = attrib(None)
    description: str = attrib(None)
    untagged_vlan: int = attrib(None)
    tagged_vlans: typing.List[int] = attrib(None)


@attrs(kw_only=True)
class interface_ref:
    device: device = attrib()
    name: str = attrib()


@attrs(kw_only=True)
class interface_list:
    interfaces: typing.List[interface] = attrib(factory=list)

    @classmethod
    def from_ansible_facts(cls, device, facts):
        ifaces = cls()

        for iface_name in facts['ansible_interfaces']:
            info = facts['ansible_{}'.format(iface_name.replace('-', '_'))]
            if 'pciid' in info:
                iface = interface(
                    name=iface_name,
                    mac_address=info['macaddress'],
                    mtu=info['mtu'],
                )

                ifaces.interfaces.append(iface)

        return ifaces
