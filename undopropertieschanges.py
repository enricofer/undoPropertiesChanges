# -*- coding: utf-8 -*-
"""
/***************************************************************************
 undoPropertiesChanges
                                 A QGIS plugin
 undoPropertiesChanges
                              -------------------
        begin                : 2014-09-04
        copyright            : (C) 2014 by Enrico Ferreguti
        email                : enricofer@gmail.com
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
# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtXml import *
from qgis.core import *
from functools import *
from qgis.utils import iface 

# Import the code for the dialog
import os.path

class trace:
    """
    class for tracing debug infos
    """

    def __init__(self):
        self.trace = None
        
    def ce(self,string):
        if self.trace:
            print string

class UndoStore:
    """
    Creates a queue object to manage the history of layer changes
    """

    def __init__(self,name):
        self.name = name
        self.history = {}
        self.FIFO = []
        self.lastPopData = {}
        self.tra = trace()

    def getName(self):
        return self.name

    def uPush(self,id,payload):
        if id in self.history:
            self.tra.ce(self.history[id])
            self.history[id].append(payload)
            self.FIFO.append(id)
            self.lastPopData = {}
        else:
            self.history[id] = []
            self.history[id].append(payload)
    
    def uPop(self):
        if not self.isEmpty():
            self.lastPopData = {'id':self.FIFO[-1],'payload':self.history[self.FIFO[-1]][-1]}
            self.history[self.FIFO[-1]].pop()
            res = {'id':self.FIFO[-1],'payload':self.history[self.FIFO[-1]][-1]}
            self.tra.ce("POP")
            self.tra.ce(self.lastPopData)
            self.tra.ce(res)
            self.FIFO.pop()
            return res
        else:
            return {}
        self.tra.ce( "history:")
        self.tra.ce( self.history)
        self.tra.ce( "ID:")
        self.tra.ce( id)
        self.tra.ce( "FIFO:")
        self.tra.ce( self.FIFO)

    def undoRemove(self,id):
        if self.history.has_key(id):
            self.history.pop(id)
        

    def last(self):
        self.tra.ce( self.FIFO[-1])
        self.tra.ce( self.history[self.FIFO[-1]])
        if not self.isEmpty():
            return {'id':self.FIFO[-1],'payload':self.history[self.FIFO[-1]]}
        else:
            return {}

    def lastId(self):
        if not self.isEmpty():
            return self.FIFO[-1]
        else:
            return ""

    def lastPop(self):
        if self.isPopped():
            res = self.lastPopData
            self.tra.ce( "lastPop:")
            self.tra.ce( res)
            self.uPush(res['id'],res['payload'])
            return res
        else:
            return None

    def isPopped(self):
        if self.lastPopData != {}:
            return True
        else:
            return None

    def isEmpty(self):
        if self.FIFO == []:
            return True
        else:
            return None

class undoPropertiesChanges:

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value("locale/userLocale")[0:2]
        localePath = os.path.join(self.plugin_dir, 'i18n', 'undolayerchanges_{}.qm'.format(locale))

        if os.path.exists(localePath):
            self.translator = QTranslator()
            self.translator.load(localePath)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)
                
        self.tra = trace()
        self.undo = {}

    def initGui(self):
        # define icons
        self.undoEnabledIcon=icon = QIcon(os.path.dirname(__file__) + "/icons/undo.png")
        self.undoDisabledIcon=icon = QIcon(os.path.dirname(__file__) + "/icons/undo-disabled.png")
        self.redoEnabledIcon=icon = QIcon(os.path.dirname(__file__) + "/icons/redo.png")
        self.redoDisabledIcon=icon = QIcon(os.path.dirname(__file__) + "/icons/redo-disabled.png")
        #define undo and redo actions
        self.uaction = QAction(self.undoDisabledIcon,"undo", self.iface.mainWindow())
        self.uaction.triggered.connect(self.undoAction)
        self.uaction.setDisabled(True)
        self.raction = QAction(self.redoDisabledIcon,"redo", self.iface.mainWindow())
        self.raction.triggered.connect(self.redoAction)
        self.raction.setDisabled(True)
        #define signals connections
        self.mapLayerRegistry = QgsMapLayerRegistry.instance()
        self.mapLayerRegistry.layersWillBeRemoved.connect(self.layersRemovedAction)
        self.mapLayerRegistry.legendLayersAdded.connect(self.layersAddedAction)
        self.iface.legendInterface().currentLayerChanged.connect(self.currentLayerChanges)
        # Add toolbar button and menu item
        self.toolBar = self.iface.addToolBar("Undo properties changes")
        self.toolBar.setObjectName("Undo properties changes")
        self.toolBar.addAction(self.uaction)
        self.toolBar.addAction(self.raction)
        self.iface.addPluginToMenu(u"&undo properties changes", self.uaction)
        self.iface.addPluginToMenu(u"&undo properties changes", self.raction)
        # register currently loaded layers
        self.layersAddedAction(iface.legendInterface().layers())
                


    def unload(self):
        # Remove the plugin menu item and icon
        self.iface.removePluginMenu(u"&undo properties changes", self.uaction)
        self.iface.removePluginMenu(u"&undo properties changes", self.raction)
        del self.toolBar
        #disconnect layer events
        self.mapLayerRegistry.legendLayersAdded.disconnect(self.layersAddedAction)
        self.mapLayerRegistry.layersWillBeRemoved.connect(self.layersRemovedAction)
        for layer in iface.legendInterface().layers():
            # disconnect signals for will removed layers
            layer.rendererChanged.disconnect()
        #del self.undo


    # recover the given layer state
    def recoverLayerState(self,recoverState):
        self.tra.ce( "RECOVERING:"+recoverState['id'])
        layer = self.mapLayerRegistry.mapLayer(recoverState['id'])
        layer.rendererChanged.disconnect()
        layer.readLayerXML(recoverState['payload'])
        self.iface.actionDraw().trigger()
        layer.rendererChanged.connect(partial(self.layerChangedAction,layer.id()))
        self.canvas.refresh()
        self.iface.legendInterface().refreshLayerSymbology(layer)
        

    # performs redo action on button call
    def redoAction(self):
        if self.undo[self.lastCurrentLayer.id()].isPopped():
            self.tra.ce("REDO ACTION:")
            self.recoverLayerState(self.undo[self.lastCurrentLayer.id()].lastPop())
            self.currentLayerChanges(self.lastCurrentLayer)
            

    # performs undo action on button call
    def undoAction(self):
        if not self.undo[self.lastCurrentLayer.id()].isEmpty():
            self.recoverLayerState(self.undo[self.lastCurrentLayer.id()].uPop())
            self.currentLayerChanges(self.lastCurrentLayer)
            

    # method connected to mapLayerRegistry.legendLayersAdded signal
    def layersAddedAction(self,layerAddedList):
        self.tra.ce( "ADDED LAYERS")
        self.tra.ce( layerAddedList)
        for layer in layerAddedList:
            self.undo[layer.id()] = UndoStore(layer.name())
            self.undo[layer.id()].uPush(layer.id(),self.getDomDef(layer))
            # connection to rendererChanged signal for added layers sending layer id
            layer.rendererChanged.connect(partial(self.layerChangedAction,layer.id()))
        self.tra.ce(self.undo)
    
    # method connected to mapLayerRegistry.layersWillBeRemoved signal
    def layersRemovedAction(self,layerRemovedList):
        self.tra.ce(layerRemovedList)
        if layerRemovedList == []:
            self.tra.ce( "REMOVED LAYERS")
            self.tra.ce( layerRemovedList)
        else:
            self.tra.ce( "MOVED LAYER")
        for layerId in layerRemovedList:
            #self.tra.ce( "REMOVED:")
            #self.tra.ce( layerId)
            del self.undo[layerId]
            # disconnect signals for will removed layers
            layer = self.mapLayerRegistry.mapLayer(layerId)
            layer.rendererChanged.disconnect()

    #method to get xml definition of layer state
    def getDomDef(self,layer):
        XMLDocument = QDomDocument("undo-layer")
        XMLMapLayers = QDomElement()
        XMLMapLayers = XMLDocument.createElement("maplayers")
        XMLMapLayer = QDomElement()
        XMLMapLayer = XMLDocument.createElement("maplayer")
        layer.writeLayerXML(XMLMapLayer,XMLDocument)
        XMLMapLayers.appendChild( XMLMapLayer )
        XMLDocument.appendChild( XMLMapLayers )
        return XMLMapLayer
    
    #method to update toolbar icons on layer change
    def currentLayerChanges(self,layer):
        self.tra.ce(self.undo.keys())
        try:
            self.tra.ce( "current layer:"+layer.name())
            self.lastCurrentLayer=layer
        except:
            return
        if layer.id() in self.undo.keys():
            if self.undo[layer.id()].isEmpty():
                self.uaction.setIcon(self.undoDisabledIcon)
                self.uaction.setDisabled(True)
            else:
                self.uaction.setIcon(self.undoEnabledIcon)
                self.uaction.setEnabled(True)
            if not self.undo[layer.id()].isPopped():
                self.raction.setIcon(self.redoDisabledIcon)
                self.raction.setDisabled(True)
            else:
                self.raction.setIcon(self.redoEnabledIcon)
                self.raction.setEnabled(True)
        

    #method connected to layer.rendererChanged signal
    def layerChangedAction(self,layerId):
        self.tra.ce("CHANGED")
        self.tra.ce( layerId)
        layer = self.mapLayerRegistry.mapLayer(layerId)
        self.undo[layerId].uPush(layerId,self.getDomDef(layer))
        #update icons
        self.currentLayerChanges(layer)
