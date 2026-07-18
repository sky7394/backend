class AIExamGenerationError(Exception):
    pass


class AIProviderConfigurationError(AIExamGenerationError):
    pass


class AIProviderCommunicationError(AIExamGenerationError):
    pass


class AIProviderResponseError(AIExamGenerationError):
    pass


class AIResponseParsingError(AIProviderResponseError):
    pass


class AIResponseValidationError(AIExamGenerationError):
    pass
