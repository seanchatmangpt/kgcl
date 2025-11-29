"""Missing methods for YDecomposition class.

Copy these methods to src/kgcl/yawl/elements/y_decomposition.py

NOTE: This file wraps methods in a class for syntax validation.
When copying to the actual class, copy only the method definitions.
"""

from __future__ import annotations

from typing import Any


class YDecompositionStubs:
    """Generated stubs for missing YDecomposition methods."""

    def addData(self, element: Element) -> None:
        """TODO: Implement addData.

        Java signature: void addData(Element element)
        """
        pass

    def addData(self, pmgr: YPersistenceManager, element: Element) -> None:
        """TODO: Implement addData.

        Java signature: void addData(YPersistenceManager pmgr, Element element)
        """
        pass

    def assignData(self, variable: Element) -> None:
        """TODO: Implement assignData.

        Java signature: void assignData(Element variable)
        """
        pass

    def assignData(self, pmgr: YPersistenceManager, variable: Element) -> None:
        """TODO: Implement assignData.

        Java signature: void assignData(YPersistenceManager pmgr, Element variable)
        """
        pass

    def clone(self) -> object:
        """TODO: Implement clone.

        Java signature: Object clone()
        """
        raise NotImplementedError

    def clone(self) -> object:
        """TODO: Implement clone.

        Java signature: Object clone()
        """
        raise NotImplementedError

    def getAttributes(self) -> YAttributeMap:
        """TODO: Implement getAttributes.

        Java signature: YAttributeMap getAttributes()
        """
        raise NotImplementedError

    def getCodelet(self) -> str:
        """TODO: Implement getCodelet.

        Java signature: String getCodelet()
        """
        return ""

    def getCodelet(self) -> str:
        """TODO: Implement getCodelet.

        Java signature: String getCodelet()
        """
        return ""

    def getDocumentation(self) -> str:
        """TODO: Implement getDocumentation.

        Java signature: String getDocumentation()
        """
        return ""

    def getID(self) -> str:
        """TODO: Implement getID.

        Java signature: String getID()
        """
        return ""

    def getInputParameters(self) -> dict:
        """TODO: Implement getInputParameters.

        Java signature: Map getInputParameters()
        """
        return {}

    def getInternalDataDocument(self) -> Document:
        """TODO: Implement getInternalDataDocument.

        Java signature: Document getInternalDataDocument()
        """
        raise NotImplementedError

    def getInternalDataDocument(self) -> Document:
        """TODO: Implement getInternalDataDocument.

        Java signature: Document getInternalDataDocument()
        """
        raise NotImplementedError

    def getLogPredicate(self) -> YLogPredicate:
        """TODO: Implement getLogPredicate.

        Java signature: YLogPredicate getLogPredicate()
        """
        raise NotImplementedError

    def getLogPredicate(self) -> YLogPredicate:
        """TODO: Implement getLogPredicate.

        Java signature: YLogPredicate getLogPredicate()
        """
        raise NotImplementedError

    def getName(self) -> str:
        """TODO: Implement getName.

        Java signature: String getName()
        """
        return ""

    def getNetDataDocument(self, netData: str) -> Document:
        """TODO: Implement getNetDataDocument.

        Java signature: Document getNetDataDocument(String netData)
        """
        raise NotImplementedError

    def getOutputData(self) -> Document:
        """TODO: Implement getOutputData.

        Java signature: Document getOutputData()
        """
        raise NotImplementedError

    def getOutputData(self) -> Document:
        """TODO: Implement getOutputData.

        Java signature: Document getOutputData()
        """
        raise NotImplementedError

    def getOutputParameters(self) -> dict:
        """TODO: Implement getOutputParameters.

        Java signature: Map getOutputParameters()
        """
        return {}

    def getOutputQueries(self) -> set:
        """TODO: Implement getOutputQueries.

        Java signature: Set getOutputQueries()
        """
        raise NotImplementedError

    def getOutputQueries(self) -> set:
        """TODO: Implement getOutputQueries.

        Java signature: Set getOutputQueries()
        """
        raise NotImplementedError

    def getRootDataElementName(self) -> str:
        """TODO: Implement getRootDataElementName.

        Java signature: String getRootDataElementName()
        """
        return ""

    def getRootDataElementName(self) -> str:
        """TODO: Implement getRootDataElementName.

        Java signature: String getRootDataElementName()
        """
        return ""

    def getSpecification(self) -> YSpecification:
        """TODO: Implement getSpecification.

        Java signature: YSpecification getSpecification()
        """
        raise NotImplementedError

    def getSpecification(self) -> YSpecification:
        """TODO: Implement getSpecification.

        Java signature: YSpecification getSpecification()
        """
        raise NotImplementedError

    def getStateSpaceBypassParams(self) -> dict:
        """TODO: Implement getStateSpaceBypassParams.

        Java signature: Map getStateSpaceBypassParams()
        """
        return {}

    def getStateSpaceBypassParams(self) -> dict:
        """TODO: Implement getStateSpaceBypassParams.

        Java signature: Map getStateSpaceBypassParams()
        """
        return {}

    def getVariableDataByName(self, name: str) -> Element:
        """TODO: Implement getVariableDataByName.

        Java signature: Element getVariableDataByName(String name)
        """
        raise NotImplementedError

    def getVariableDataByName(self, name: str) -> Element:
        """TODO: Implement getVariableDataByName.

        Java signature: Element getVariableDataByName(String name)
        """
        raise NotImplementedError

    def initialise(self) -> None:
        """TODO: Implement initialise.

        Java signature: void initialise()
        """
        pass

    def initialise(self, pmgr: YPersistenceManager) -> None:
        """TODO: Implement initialise.

        Java signature: void initialise(YPersistenceManager pmgr)
        """
        pass

    def initializeDataStore(self, pmgr: YPersistenceManager, casedata: YNetData) -> None:
        """TODO: Implement initializeDataStore.

        Java signature: void initializeDataStore(YPersistenceManager pmgr, YNetData casedata)
        """
        pass

    def initializeDataStore(self, casedata: YNetData) -> None:
        """TODO: Implement initializeDataStore.

        Java signature: void initializeDataStore(YNetData casedata)
        """
        pass

    def paramMapToXML(self, paramMap: dict) -> str:
        """TODO: Implement paramMapToXML.

        Java signature: String paramMapToXML(Map paramMap)
        """
        return ""

    def paramMapToXML(self, paramMap: dict) -> str:
        """TODO: Implement paramMapToXML.

        Java signature: String paramMapToXML(Map paramMap)
        """
        return ""

    def removeInputParameter(self, name: str) -> YParameter:
        """TODO: Implement removeInputParameter.

        Java signature: YParameter removeInputParameter(String name)
        """
        raise NotImplementedError

    def removeInputParameter(self, parameter: YParameter) -> YParameter:
        """TODO: Implement removeInputParameter.

        Java signature: YParameter removeInputParameter(YParameter parameter)
        """
        raise NotImplementedError

    def removeOutputParameter(self, name: str) -> YParameter:
        """TODO: Implement removeOutputParameter.

        Java signature: YParameter removeOutputParameter(String name)
        """
        raise NotImplementedError

    def removeOutputParameter(self, parameter: YParameter) -> YParameter:
        """TODO: Implement removeOutputParameter.

        Java signature: YParameter removeOutputParameter(YParameter parameter)
        """
        raise NotImplementedError

    def requiresResourcingDecisions(self) -> bool:
        """TODO: Implement requiresResourcingDecisions.

        Java signature: boolean requiresResourcingDecisions()
        """
        return False

    def requiresResourcingDecisions(self) -> bool:
        """TODO: Implement requiresResourcingDecisions.

        Java signature: boolean requiresResourcingDecisions()
        """
        return False

    def restoreData(self, casedata: YNetData) -> None:
        """TODO: Implement restoreData.

        Java signature: void restoreData(YNetData casedata)
        """
        pass

    def setAttributes(self, attributes: dict) -> None:
        """TODO: Implement setAttributes.

        Java signature: void setAttributes(Map attributes)
        """
        pass

    def setCodelet(self, codelet: str) -> None:
        """TODO: Implement setCodelet.

        Java signature: void setCodelet(String codelet)
        """
        pass

    def setCodelet(self, codelet: str) -> None:
        """TODO: Implement setCodelet.

        Java signature: void setCodelet(String codelet)
        """
        pass

    def setDocumentation(self, documentation: str) -> None:
        """TODO: Implement setDocumentation.

        Java signature: void setDocumentation(String documentation)
        """
        pass

    def setEnablementParameter(self, parameter: YParameter) -> None:
        """TODO: Implement setEnablementParameter.

        Java signature: void setEnablementParameter(YParameter parameter)
        """
        pass

    def setExternalInteraction(self, interaction: bool) -> None:
        """TODO: Implement setExternalInteraction.

        Java signature: void setExternalInteraction(boolean interaction)
        """
        pass

    def setExternalInteraction(self, interaction: bool) -> None:
        """TODO: Implement setExternalInteraction.

        Java signature: void setExternalInteraction(boolean interaction)
        """
        pass

    def setID(self, id: str) -> None:
        """TODO: Implement setID.

        Java signature: void setID(String id)
        """
        pass

    def setLogPredicate(self, predicate: YLogPredicate) -> None:
        """TODO: Implement setLogPredicate.

        Java signature: void setLogPredicate(YLogPredicate predicate)
        """
        pass

    def setLogPredicate(self, predicate: YLogPredicate) -> None:
        """TODO: Implement setLogPredicate.

        Java signature: void setLogPredicate(YLogPredicate predicate)
        """
        pass

    def setName(self, name: str) -> None:
        """TODO: Implement setName.

        Java signature: void setName(String name)
        """
        pass

    def setOutputExpression(self, query: str) -> None:
        """TODO: Implement setOutputExpression.

        Java signature: void setOutputExpression(String query)
        """
        pass

    def setOutputExpression(self, query: str) -> None:
        """TODO: Implement setOutputExpression.

        Java signature: void setOutputExpression(String query)
        """
        pass

    def setSpecification(self, specification: YSpecification) -> None:
        """TODO: Implement setSpecification.

        Java signature: void setSpecification(YSpecification specification)
        """
        pass

    def setSpecification(self, specification: YSpecification) -> None:
        """TODO: Implement setSpecification.

        Java signature: void setSpecification(YSpecification specification)
        """
        pass

    def toString(self) -> str:
        """TODO: Implement toString.

        Java signature: String toString()
        """
        return ""

    def toString(self) -> str:
        """TODO: Implement toString.

        Java signature: String toString()
        """
        return ""

    def toXML(self) -> str:
        """TODO: Implement toXML.

        Java signature: String toXML()
        """
        return ""

    def toXML(self) -> str:
        """TODO: Implement toXML.

        Java signature: String toXML()
        """
        return ""

    def verify(self, handler: YVerificationHandler) -> None:
        """TODO: Implement verify.

        Java signature: void verify(YVerificationHandler handler)
        """
        pass

    def verify(self, handler: YVerificationHandler) -> None:
        """TODO: Implement verify.

        Java signature: void verify(YVerificationHandler handler)
        """
        pass
