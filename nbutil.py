import click
import json
import logging
import pynetbox

import resources
import netbox

LOG = logging.getLogger(__name__)

logging.basicConfig(level='DEBUG')


@click.group(
    context_settings=dict(auto_envvar_prefix='NETBOX'))
@click.option('--url', '-u')
@click.option('--token', '-t')
@click.pass_context
def main(ctx, url, token):
    ctx.obj = netbox.Netbox(url, token=token)


@main.command()
@click.option('--site', '-s', required=True)
@click.option('--device-role', '-r')
@click.argument('factfiles', nargs=-1)
@click.pass_context
def load(ctx, site, device_role, factfiles):
    api = ctx.obj
    devices = []
    for factfile in factfiles:
        with open(factfile) as fd:
            facts = json.load(fd)

        if 'ansible_facts' not in facts:
            LOG.warning('invalid fact file: %s', factfile)
            continue

        if facts['ansible_facts'].get('ansible_virtualization_role') != 'host':
            LOG.warning('skipping virtual machine: %s', factfile)
            continue

        try:
            dev = resources.device.from_ansible_facts(facts['ansible_facts'])
        except KeyError as err:
            LOG.warning('failed loading device from %s: missing %s',
                        factfile, err)
        else:
            devices.append(dev)

    for dev in devices:
        try:
            _dev = api.dcim.devices.filter(name=dev.name)[0]
        except IndexError:
            LOG.info('adding %s', dev)

            try:
                _site = api.dcim.sites.filter(name=site)[0]
            except IndexError:
                _site = api.dcim.sites.create(name=site)

            try:
                manufacturer = api.dcim.manufacturers.filter(
                    name=dev.device_type.manufacturer)[0]
            except IndexError:
                obj = resources.manufacturer(name=dev.device_type.manufacturer)
                LOG.info('create new manufacturer %s', obj)
                manufacturer = api.dcim.manufacturers.create(**obj.to_dict())

            try:
                devtype = api.dcim.device_types.filter(
                    manufacturer_name=manufacturer.name,
                    model=dev.device_type.model)[0]
            except IndexError:
                obj = resources.device_type(
                    manufacturer=manufacturer.id,
                    model=dev.device_type.model)
                LOG.info('create new device type %s', obj)
                devtype = api.dcim.device_types.create(**obj.to_dict())

            try:
                devrole = api.dcim.device_roles.filter(
                    name=dev.device_role)[0]
            except IndexError:
                obj = resources.device_role(name=dev.device_role)
                LOG.info('create new device role %s', obj)
                devrole = api.dcim.device_roles.create(**obj.to_dict())

            dev.site = _site.id
            dev.device_type = devtype.id
            dev.device_role = devrole.id

            try:
                _dev = api.dcim.devices.create(**dev.to_dict())
            except pynetbox.core.query.RequestError as err:
                breakpoint()
                ...

        for interface in dev.interfaces.interfaces:
            try:
                _iface = api.dcim.interfaces.filter(
                    device_id=_dev.id, name=interface.name)[0]
            except IndexError:
                LOG.info('create new interface %s on %s', interface, dev)
                _iface = api.dcim.interfaces.create(
                    device=_dev.id, **interface.to_dict())


if __name__ == '__main__':
    main()
