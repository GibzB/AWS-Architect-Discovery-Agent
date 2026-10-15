# Architecture Diagram — CDS Agentic Omnichannel Engagement

AWS Communication Developer Services (SES, End User Messaging SMS/RCS, End User
Messaging Social/WhatsApp) are the communications backbone; Amazon Bedrock
(Nova Sonic + Nova Pro) provides the agentic reasoning. Render the Mermaid below
with any Mermaid viewer, or see `ARCHITECTURE.md` for the service breakdown.

```mermaid
flowchart TB
    subgraph Client["Customer touchpoints"]
        Browser["Browser (voice UI)"]
        Phone["Phone / Messaging app"]
        Inbox["Email inbox"]
    end

    subgraph Edge["Edge & API"]
        CF["CloudFront + S3 (frontend)"]
        APIGW["API Gateway + Lambda (SigV4 presign)"]
    end

    subgraph Runtime["Amazon Bedrock AgentCore Runtime"]
        WS["FastAPI WebSocket server"]
        subgraph Channels["channels/ (channel abstraction - C-ready)"]
            SES_A["SES adapter"]
            SMS_A["SMS adapter"]
            RCS_A["RCS adapter (stub)"]
            WA_A["WhatsApp adapter (P2)"]
        end
        ENG["engagement/ orchestrator - intent - actions - state"]
    end

    subgraph AI["Amazon Bedrock"]
        Sonic["Nova Sonic (bidirectional voice)"]
        Pro["Nova Pro (report + intent routing)"]
        KB["Knowledge Base (RAG)"]
    end

    subgraph CDS["AWS Communication Developer Services"]
        SES["Amazon SES"]
        EUM["AWS End User Messaging SMS / RCS"]
        SOCIAL["End User Messaging Social - WhatsApp (P2)"]
    end

    subgraph Inbound["Two-way inbound"]
        SNS["SNS topic (inbound events)"]
        InLambda["Inbound Lambda: verify - intent - action - reply"]
    end

    DDB[("DynamoDB: sessions + conversation state")]

    Browser -->|request URL| APIGW
    APIGW -->|wss| WS
    Browser <-->|voice stream| WS
    CF --- Browser

    WS <--> Sonic
    WS --> Pro
    Pro --- KB
    WS --> ENG
    ENG --> Channels

    SES_A --> SES
    SMS_A --> EUM
    RCS_A -.-> EUM
    WA_A -.-> SOCIAL

    SES --> Inbox
    EUM --> Phone

    Phone -->|reply| EUM
    EUM --> SNS --> InLambda
    InLambda --> Pro
    InLambda --> Channels
    InLambda <--> DDB
    ENG <--> DDB
    WS --> DDB
```
