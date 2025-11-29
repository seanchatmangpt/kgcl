"""Missing methods for YVariable class.

Copy these methods to src/kgcl/yawl/elements/y_decomposition.py

NOTE: This file wraps methods in a class for syntax validation.
When copying to the actual class, copy only the method definitions.
"""

from __future__ import annotations

from typing import Any


class YVariableStubs:
    """Generated stubs for missing YVariable methods."""

    def addAttribute(self, name: str, value: DynamicValue) -> None:
        """TODO: Implement addAttribute.

        Java signature: void addAttribute(String name, DynamicValue value)
        """
        pass

    def addAttribute(self, key: str, value: str) -> None:
        """TODO: Implement addAttribute.

        Java signature: void addAttribute(String key, String value)
        """
        pass

    def checkDataTypeValue(self, value: Element) -> None:
        """TODO: Implement checkDataTypeValue.

        Java signature: void checkDataTypeValue(Element value)
        """
        pass

    def checkValue(self, value: str, label: str, handler: YVerificationHandler) -> None:
        """TODO: Implement checkValue.

        Java signature: void checkValue(String value, String label, YVerificationHandler handler)
        """
        pass

    def clone(self) -> object:
        """TODO: Implement clone.

        Java signature: Object clone()
        """
        raise NotImplementedError

    def compareTo(self, other: YVariable) -> int:
        """TODO: Implement compareTo.

        Java signature: int compareTo(YVariable other)
        """
        return 0

    def getAttributes(self) -> YAttributeMap:
        """TODO: Implement getAttributes.

        Java signature: YAttributeMap getAttributes()
        """
        raise NotImplementedError

    def getDataTypeName(self) -> str:
        """TODO: Implement getDataTypeName.

        Java signature: String getDataTypeName()
        """
        return ""

    def getDataTypeNameSpace(self) -> str:
        """TODO: Implement getDataTypeNameSpace.

        Java signature: String getDataTypeNameSpace()
        """
        return ""

    def getDataTypeNameUnprefixed(self) -> str:
        """TODO: Implement getDataTypeNameUnprefixed.

        Java signature: String getDataTypeNameUnprefixed()
        """
        return ""

    def getDataTypePrefix(self) -> str:
        """TODO: Implement getDataTypePrefix.

        Java signature: String getDataTypePrefix()
        """
        return ""

    def getDefaultValue(self) -> str:
        """TODO: Implement getDefaultValue.

        Java signature: String getDefaultValue()
        """
        return ""

    def getDocumentation(self) -> str:
        """TODO: Implement getDocumentation.

        Java signature: String getDocumentation()
        """
        return ""

    def getElementName(self) -> str:
        """TODO: Implement getElementName.

        Java signature: String getElementName()
        """
        return ""

    def getInitialValue(self) -> str:
        """TODO: Implement getInitialValue.

        Java signature: String getInitialValue()
        """
        return ""

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

    def getOrdering(self) -> int:
        """TODO: Implement getOrdering.

        Java signature: int getOrdering()
        """
        return 0

    def getParentDecomposition(self) -> YDecomposition:
        """TODO: Implement getParentDecomposition.

        Java signature: YDecomposition getParentDecomposition()
        """
        raise NotImplementedError

    def getPreferredName(self) -> str:
        """TODO: Implement getPreferredName.

        Java signature: String getPreferredName()
        """
        return ""

    def hasAttributes(self) -> bool:
        """TODO: Implement hasAttributes.

        Java signature: boolean hasAttributes()
        """
        return False

    def isEmptyTyped(self) -> bool:
        """TODO: Implement isEmptyTyped.

        Java signature: boolean isEmptyTyped()
        """
        return False

    def isMandatory(self) -> bool:
        """TODO: Implement isMandatory.

        Java signature: boolean isMandatory()
        """
        return False

    def isOptional(self) -> bool:
        """TODO: Implement isOptional.

        Java signature: boolean isOptional()
        """
        return False

    def isRequired(self) -> bool:
        """TODO: Implement isRequired.

        Java signature: boolean isRequired()
        """
        return False

    def isSchemaVersionAtLeast2_1(self) -> bool:
        """TODO: Implement isSchemaVersionAtLeast2_1.

        Java signature: boolean isSchemaVersionAtLeast2_1()
        """
        return False

    def isUntyped(self) -> bool:
        """TODO: Implement isUntyped.

        Java signature: boolean isUntyped()
        """
        return False

    def isUserDefinedType(self) -> bool:
        """TODO: Implement isUserDefinedType.

        Java signature: boolean isUserDefinedType()
        """
        return False

    def isValidTypeNameForSchema(self, dataTypeName: str) -> bool:
        """TODO: Implement isValidTypeNameForSchema.

        Java signature: boolean isValidTypeNameForSchema(String dataTypeName)
        """
        return False

    def requiresInputValue(self) -> bool:
        """TODO: Implement requiresInputValue.

        Java signature: boolean requiresInputValue()
        """
        return False

    def setAttributes(self, attributes: dict) -> None:
        """TODO: Implement setAttributes.

        Java signature: void setAttributes(Map attributes)
        """
        pass

    def setDataTypeAndName(self, dataType: str, name: str, namespace: str) -> None:
        """TODO: Implement setDataTypeAndName.

        Java signature: void setDataTypeAndName(String dataType, String name, String namespace)
        """
        pass

    def setDefaultValue(self, value: str) -> None:
        """TODO: Implement setDefaultValue.

        Java signature: void setDefaultValue(String value)
        """
        pass

    def setDocumentation(self, documentation: str) -> None:
        """TODO: Implement setDocumentation.

        Java signature: void setDocumentation(String documentation)
        """
        pass

    def setElementName(self, elementName: str) -> None:
        """TODO: Implement setElementName.

        Java signature: void setElementName(String elementName)
        """
        pass

    def setEmptyTyped(self, empty: bool) -> None:
        """TODO: Implement setEmptyTyped.

        Java signature: void setEmptyTyped(boolean empty)
        """
        pass

    def setInitialValue(self, initialValue: str) -> None:
        """TODO: Implement setInitialValue.

        Java signature: void setInitialValue(String initialValue)
        """
        pass

    def setLogPredicate(self, predicate: YLogPredicate) -> None:
        """TODO: Implement setLogPredicate.

        Java signature: void setLogPredicate(YLogPredicate predicate)
        """
        pass

    def setMandatory(self, mandatory: bool) -> None:
        """TODO: Implement setMandatory.

        Java signature: void setMandatory(boolean mandatory)
        """
        pass

    def setName(self, name: str) -> None:
        """TODO: Implement setName.

        Java signature: void setName(String name)
        """
        pass

    def setOptional(self, option: bool) -> None:
        """TODO: Implement setOptional.

        Java signature: void setOptional(boolean option)
        """
        pass

    def setOrdering(self, ordering: int) -> None:
        """TODO: Implement setOrdering.

        Java signature: void setOrdering(int ordering)
        """
        pass

    def setParentDecomposition(self, parentDecomposition: YDecomposition) -> None:
        """TODO: Implement setParentDecomposition.

        Java signature: void setParentDecomposition(YDecomposition parentDecomposition)
        """
        pass

    def setUntyped(self, isUntyped: bool) -> None:
        """TODO: Implement setUntyped.

        Java signature: void setUntyped(boolean isUntyped)
        """
        pass

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

    def toXMLGuts(self) -> str:
        """TODO: Implement toXMLGuts.

        Java signature: String toXMLGuts()
        """
        return ""

    def usesElementDeclaration(self) -> bool:
        """TODO: Implement usesElementDeclaration.

        Java signature: boolean usesElementDeclaration()
        """
        return False

    def usesTypeDeclaration(self) -> bool:
        """TODO: Implement usesTypeDeclaration.

        Java signature: boolean usesTypeDeclaration()
        """
        return False

    def verify(self, handler: YVerificationHandler) -> None:
        """TODO: Implement verify.

        Java signature: void verify(YVerificationHandler handler)
        """
        pass
