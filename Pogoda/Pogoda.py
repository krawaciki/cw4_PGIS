# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Pogoda
                                 A QGIS plugin
 Pogoda
                              -------------------
        begin                : 2015-01-06
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Tomasz Krawczyk
        email                : krawaciki@wp.pl
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from Pogoda_dialog import PogodaDialog
import os.path
import urllib2
import json
import datetime
import time
from qgis.core import *
import os


class Pogoda:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'Pogoda_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = PogodaDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Pogoda')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'Pogoda')
        self.toolbar.setObjectName(u'Pogoda')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('Pogoda', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/Pogoda/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Pogoda'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Pogoda'),
                action)
            self.iface.removeToolBarIcon(action)


    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            warstwa = self.plugin_dir + '/shp/admin_region_teryt_woj.shp'
            mapa = QgsVectorLayer(warstwa, 'mapaPogody', 'ogr')
            warunek = self.plugin_dir + '/shp/do_daty.txt'           
            
            datamod = time.ctime(os.path.getmtime(warunek))
            datamodyf = datetime.datetime.strptime(datamod, '%a %b %d %H:%M:%S %Y')
            dataob = datetime.datetime.now()

            if (((dataob-datamodyf).seconds/60)>10):
                ids=''
                for x in mapa.getFeatures():
                    if (ids == ''):
                        ids = str(x.attributes()[1])
                    else:
                        ids = ids + ',' + str(x.attributes()[1])
                
                adres = 'http://api.openweathermap.org/data/2.5/group?id=' + ids + '&units=metric'
                content = urllib2.urlopen(adres).read()
                slow_json = json.loads(content)
                for x in mapa.getFeatures():
                    for i in xrange(0, len(slow_json['list'])):
                        if x.attributes()[1] == slow_json['list'][i]['id']:
                            temperatura={mapa.fieldNameIndex('temperatura'):slow_json['list'][i]['main']['temp']}
                            temp_max={mapa.fieldNameIndex('temp_max'): slow_json['list'][i]['main']['temp_max']}
                            temp_min={mapa.fieldNameIndex('temp_min'): slow_json['list'][i]['main']['temp_min']}
                            cis_atm={mapa.fieldNameIndex('cis_atm'): slow_json['list'][i]['main']['pressure']}
                            wilgotnosc={mapa.fieldNameIndex('wilgotnosc'): slow_json['list'][i]['main']['humidity']}
                            predk_wiatr={mapa.fieldNameIndex('predk_wiatr'): slow_json['list'][i]['wind']['speed']}
                            kier_wiatr={mapa.fieldNameIndex('kier_wiatr'): slow_json['list'][i]['wind']['deg']}
                            infor_o_chmur={mapa.fieldNameIndex('infor_o_chmur'): slow_json['list'][i]['clouds']['all']}
                            mapa.startEditing()
                            mapa.dataProvider().changeAttributeValues({x.id():temperatura})
                            mapa.dataProvider().changeAttributeValues({x.id():temp_max})
                            mapa.dataProvider().changeAttributeValues({x.id():temp_min})
                            mapa.dataProvider().changeAttributeValues({x.id():cis_atm})
                            mapa.dataProvider().changeAttributeValues({x.id():wilgotnosc})
                            mapa.dataProvider().changeAttributeValues({x.id():predk_wiatr})
                            mapa.dataProvider().changeAttributeValues({x.id():kier_wiatr})
                            mapa.dataProvider().changeAttributeValues({x.id():infor_o_chmur})
                            mapa.commitChanges()
                plik = open(warunek, 'w')
                plik.write('')
                plik.close()
                print ((dataob-datamodyf).seconds/60)
            else:
                print ((dataob-datamodyf).seconds/60)

            QgsMapLayerRegistry.instance().addMapLayer(mapa)

            pass
