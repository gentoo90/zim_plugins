# -*- coding: utf-8 -*-
'''Plugin to create pages from Jira issues'''

import gtk
import gnomekeyring
from jira.client import JIRA

from zim.fs import TmpFile
from zim.plugins import PluginClass, WindowExtension, DialogExtension, extends
from zim.actions import action
import zim.templates
from zim.exporter import StaticLinker
from zim.gui.widgets import Dialog

APP_NAME = 'My Jira Issues'

def get_passwd(address, username):
    kr = gnomekeyring.get_default_keyring_sync()
    attr = {
        'username': username,
        'address': address,
        'application': APP_NAME
    }
    try:
        result_list = gnomekeyring.find_items_sync(gnomekeyring.ITEM_GENERIC_SECRET, attr)
    except gnomekeyring.NoMatchError:
        passwd = getpass('Password: ')
        gnomekeyring.item_create_sync(kr, gnomekeyring.ITEM_GENERIC_SECRET, address, attr, passwd, True)
        return passwd

    passwds = [result.secret for result in result_list]
    if len(passwds) > 1:
        raise Exception('More than one password')
    return passwds[0]

ui_xml = '''
    <ui>
        <menubar name='menubar'>
            <menu action='file_menu'>
                <placeholder name='open_items'>
                    <menuitem action='import_from_jira'/>
                </placeholder>
            </menu>
        </menubar>
    </ui>
    '''

ui_actions = (
    # name, stock id, label, accelerator, tooltip, readonly
    ('import_from_jira', 'gtk-new', _('Import from _Jira'), '<ctrl><shift>J', '', False), # T: menu item
)


class ImportFromJira(PluginClass):

    plugin_info = {
        'name': _('Import from Jira'),
        'description': _('''\
This plugin allows to create pages based on Jira issues
'''),
        'author': 'Igor Shaula',
    }

    plugin_preferences = (
        # key, type, label, default
        ('server', 'string', _('Jira server URL'), 'https://example.com'),
        ('user', 'string', _('Jira user name'), 'user'),
        ('namespace', 'namespace', _('Namespace'), ':Jira'),
    )

    def initialize_ui(self, ui):
        if self.ui.ui_type == 'gtk':
            self.ui.add_actions(ui_actions, self)
            self.ui.add_ui(ui_xml, self)

    def import_from_jira(self):
        dialog = SelectIssueDialog.unique(self, self)
        dialog.show_all()


class SelectIssueDialog(Dialog):

    def __init__(self, plugin):
        Dialog.__init__(self, plugin.ui, _('Select issue')) # T: dialog title
        self.plugin = plugin

        hbox = gtk.HBox()
        self.vbox.add(hbox)
        hbox.add(gtk.Label(_('Issue Key') + ': ')) # T: input in 'insert screenshot' dialog
        self.entry = gtk.Entry()
        hbox.add(self.entry)

        jira_opts = {
            'server': self.plugin.preferences['server'],
            'verify': False,
        }
        self.jira = JIRA(jira_opts, basic_auth=(self.plugin.preferences['user'],
            get_passwd(str(self.plugin.preferences['server']), str(self.plugin.preferences['user']))))

    def do_response_ok(self):
        key = self.entry.get_text()
        issue = self.jira.issue(key)

        path = self.plugin.preferences['namespace'] + ':' + issue.fields.project.key + ':' + issue.key
        text = "====== %s %s ======\n" % (issue.key, issue.fields.summary)

        self.plugin.ui.new_page_from_text(text, path, open_page=True)
        return True
