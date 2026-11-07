# Project Title:

> Kisan Copilot: Autonomous Multi-Agent AI for Agricultural Decision
> Support and KCC Financial Assistance

2.  # Team Members:
    
      - > Prakhar Gupta (230486)
    
      - > Rishabh Kumar Singh (230468)

3.  # Problem Definition

> What problem are you addressing?
> 
> Small and marginal farmers often need to make interconnected decisions
> involving weather conditions, crop prices, agricultural credit, and
> crop insurance. Relevant
> 
> information is distributed across different sources and changes over
> time, making it
> 
> difficult for farmers to determine which actions are most appropriate
> for their current situation.

# Kisan Copilot addresses this problem by using a multi-agent AI system that autonomously analyzes a farmer's profile and relevant agricultural signals,

> **delegates tasks to specialized agents, combines their findings, and
> generates personalized, explainable recommendations.**
> 
> Who are the intended users?

  - > Small and marginal farmers

  - > Farmers using or eligible for **Kisan Credit Card (KCC)**-based
    > agricultural finance

  - > Banking/business-correspondent personnel who may assist farmers

  - > Agricultural support personnel

> For the academic prototype, **synthetic farmer profiles** will be used
> instead of real customer/financial data.

# Objectives & Expected Outcomes

1.  > **Develop a multi-agent AI system** capable of autonomously
    > coordinating

> specialized agents for weather, mandi prices, agricultural credit, and
> crop insurance.

# Integrate real-world agricultural information sources and tools with

> synthetic farmer/KCC profiles to generate personalized and
> context-aware recommendations.

3.  > **Implement explainability and human-in-the-loop safeguards** for
    > sensitive financial recommendations and demonstrate agentic
    > planning, tool usage,

> delegation, and decision-making.

4.  > Expected outcome: A working prototype where a farmer profile can
    > be selected

> and submitted to Kisan Copilot, after which the system determines
> which agents are relevant, retrieves required information through
> tools/APIs, reasons over the collected context, and produces
> prioritized recommendations with supporting
> 
> information and confidence/status indicators.

5.  # Proposed Methodology
    
      - > Agents and their roles

<table>
<thead>
<tr class="header">
<th><blockquote>
<p><strong>Agent</strong></p>
</blockquote></th>
<th><blockquote>
<p><strong>Responsibility</strong></p>
</blockquote></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><blockquote>
<p><strong>Orchestrato r Agent</strong></p>
</blockquote></td>
<td><blockquote>
<p>Understands the farmer's situation, plans the workflow, selects/delegates tasks to relevant agents, and synthesizes the final recommendation</p>
</blockquote></td>
</tr>
<tr class="even">
<td><blockquote>
<p><strong>Weather Agent</strong></p>
</blockquote></td>
<td><blockquote>
<p>Retrieves and analyzes weather conditions and forecasts relevant to the farmer's crop/location</p>
</blockquote></td>
</tr>
<tr class="odd">
<td><blockquote>
<p><strong>Mandi</strong></p>
<p><strong>Intelligence Agent</strong></p>
</blockquote></td>
<td><blockquote>
<p>Retrieves mandi prices and analyzes price trends to provide crop-selling/holding insights</p>
</blockquote></td>
</tr>
<tr class="even">
<td><blockquote>
<p><strong>Credit</strong></p>
<p><strong>Lifecycle Agent</strong></p>
</blockquote></td>
<td><blockquote>
<p>Analyzes synthetic KCC information such as credit limit, outstanding amount and repayment timelines</p>
</blockquote></td>
</tr>
<tr class="odd">
<td><blockquote>
<p><strong>Insurance Agent</strong></p>
</blockquote></td>
<td><blockquote>
<p>Checks PMFBY-related eligibility, enrollment and relevant crop/insurance information</p>
</blockquote></td>
</tr>
<tr class="even">
<td><blockquote>
<p><strong>Communica tion Agent</strong></p>
</blockquote></td>
<td><blockquote>
<p>Converts the final recommendation into farmer-friendly communication and, later, Hindi/Indian-language voice output</p>
</blockquote></td>
</tr>
</tbody>
</table>

  - > Tools/APIs to be used

<!-- end list -->

1.  # IMD / weather data APIs

2.  > **AgMarkNet** for mandi/market-price information

3.  > **PostgreSQL** for synthetic farmer and KCC profiles

4.  > **Redis** for caching frequently accessed information

5.  # PMFBY/public government information sources

6.  > **Bhashini APIs** for speech/language capabilities in later stages

7.  > Optional **WhatsApp Cloud API** for future farmer communication

8.  > **MCP-based tool wrappers** as an advanced extension
    
      - > LLM/model and Agentic AI framework

> **LLM:** Llama model accessed through **Groq API Agentic AI Framework:
> CrewAI**
> 
> **Backend:** FastAPI
> 
> **Database:** PostgreSQL
> 
> **Caching:** Redis
> 
> **Frontend:** React + Tailwind CSS
> 
> **Advanced components:** LangSmith, pgvector/RAG, MCP

  - > Brief workflow of the proposed system

> ![](media/image1.png)

6.  # Feasibility & Resources
    
      - > Data sources
        
        1.  > Synthetic farmer/KCC profiles
        
        2.  > IMD weather information
        
        3.  > AgMarkNet mandi prices
        
        4.  > PMFBY/public agricultural insurance information
        
        5.  > Government agricultural/KCC documentation for later RAG
            > implementation
    
      - > APIs/tools
        
        1.  > Groq API
        
        2.  > IMD/weather APIs
        
        3.  > AgMarkNet
        
        4.  > PostgreSQL
        
        5.  > Redis
        
        6.  > Bhashini
        
        7.  > Optional WhatsApp Cloud API
        
        8.  > MCP tool interfaces
    
      - > Software/frameworks
        
        1.  > Python
        
        2.  > FastAPI
        
        3.  > CrewAI
        
        4.  > PostgreSQL
        
        5.  > Redis
        
        6.  > React
        
        7.  > Tailwind CSS
        
        8.  > LangSmith
        
        9.  > pgvector
        
        10. > Git/GitHub
        
        11. > Docker
        
        12. > WSL2
    
      - > Compute/resources required

> The core system is designed to run without a dedicated GPU because the
> LLM inference is accessed through the Groq API. Development can
> therefore be
> 
> performed on a standard laptop with approximately **12 GB RAM and an
> Intel i3 processor**, while heavier external model inference is
> handled through cloud
> 
> APIs.

# Team Members & Individual Understanding

<table>
<thead>
<tr class="header">
<th><strong>Member</strong></th>
<th><blockquote>
<p><strong>Role/Responsibility</strong></p>
</blockquote></th>
<th><blockquote>
<p><strong>Individual Understanding</strong></p>
</blockquote></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><blockquote>
<p>Prakhar Gupta</p>
</blockquote></td>
<td><blockquote>
<p>System Architecture, Orchestrator Agent, Backend &amp; Database Integration, Agent</p>
<p>Coordination</p>
</blockquote></td>
<td><blockquote>
<p>Understands the complete system architecture,</p>
<p>CrewAI orchestration,</p>
<p>agent delegation, FastAPI backend, PostgreSQL data flow, tool integration and</p>
</blockquote></td>
</tr>
</tbody>
</table>

<table>
<thead>
<tr class="header">
<th></th>
<th></th>
<th><blockquote>
<p>overall Agentic AI workflow</p>
</blockquote></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><blockquote>
<p>Rishabh Kumar Singh</p>
</blockquote></td>
<td><blockquote>
<p>Specialized Agent</p>
<p>Development, API/Tool Integration, Frontend &amp; Testing</p>
</blockquote></td>
<td><blockquote>
<p>Understands specialized agent implementation, external API/tool</p>
<p>integration, React interface, agent</p>
<p>communication, testing and evaluation of the system</p>
</blockquote></td>
</tr>
</tbody>
</table>

# Project Timeline

<table>
<thead>
<tr class="header">
<th><blockquote>
<p><strong>Activity</strong></p>
</blockquote></th>
<th><blockquote>
<p><strong>Week(s)</strong></p>
</blockquote></th>
<th><blockquote>
<p><strong>Deliverable</strong></p>
</blockquote></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><blockquote>
<p>Problem &amp; Design</p>
</blockquote></td>
<td><blockquote>
<p>Week 1</p>
</blockquote></td>
<td><blockquote>
<p>Final problem definition,</p>
<p>architecture, agent roles, technology</p>
<p>selection and database</p>
<p>design</p>
</blockquote></td>
</tr>
<tr class="even">
<td><blockquote>
<p>Development /Coding</p>
</blockquote></td>
<td><blockquote>
<p>Week 2–5</p>
</blockquote></td>
<td><blockquote>
<p>FastAPI backend, PostgreSQL database,</p>
<p>Weather/Man di/Credit/Insu rance agents, tools and</p>
<p>Orchestrator</p>
</blockquote></td>
</tr>
<tr class="odd">
<td><blockquote>
<p>Integration &amp; Testing/Debugging</p>
</blockquote></td>
<td><blockquote>
<p>Week 5–6</p>
</blockquote></td>
<td><blockquote>
<p>Multi-agent integration, API</p>
<p>integration, workflow testing and error</p>
<p>handling</p>
</blockquote></td>
</tr>
</tbody>
</table>

<table>
<thead>
<tr class="header">
<th><blockquote>
<p><strong>Activity</strong></p>
</blockquote></th>
<th><blockquote>
<p><strong>Week(s)</strong></p>
</blockquote></th>
<th><blockquote>
<p><strong>Deliverable</strong></p>
</blockquote></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td></td>
<td></td>
<td></td>
</tr>
<tr class="even">
<td><blockquote>
<p>Evaluation &amp; Refinement</p>
</blockquote></td>
<td><blockquote>
<p>Week 6–7</p>
</blockquote></td>
<td><blockquote>
<p>Scenario-bas ed</p>
<p>evaluation, accuracy/re sponse</p>
<p>analysis, debugging and system refinement</p>
</blockquote></td>
</tr>
<tr class="odd">
<td><blockquote>
<p>Presentation/Interface UI</p>
</blockquote></td>
<td><blockquote>
<p>Week 6–7</p>
</blockquote></td>
<td><blockquote>
<p>React</p>
<p>dashboard showing</p>
<p>farmer profile, agent activity and final recommendati ons</p>
</blockquote></td>
</tr>
<tr class="even">
<td><blockquote>
<p>Deployment</p>
</blockquote></td>
<td><blockquote>
<p>Week 7</p>
</blockquote></td>
<td><blockquote>
<p>Local/contai nerized</p>
<p>deployment and final system setup</p>
</blockquote></td>
</tr>
<tr class="odd">
<td><blockquote>
<p>Final Demo</p>
</blockquote></td>
<td></td>
<td><blockquote>
<p>End-to-end demonstration</p>
<p>,</p>
</blockquote></td>
</tr>
</tbody>
</table>

<table>
<thead>
<tr class="header">
<th><blockquote>
<p><strong>Activity</strong></p>
</blockquote></th>
<th><blockquote>
<p><strong>Week(s)</strong></p>
</blockquote></th>
<th><blockquote>
<p><strong>Deliverable</strong></p>
</blockquote></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td></td>
<td><blockquote>
<p>Week 8</p>
</blockquote></td>
<td><blockquote>
<p>documentatio n, PPT, report and viva</p>
<p>preparation</p>
</blockquote></td>
</tr>
</tbody>
</table>

# Team Responsibility Matrix

<table>
<thead>
<tr class="header">
<th><blockquote>
<p><strong>Activity</strong></p>
</blockquote></th>
<th><blockquote>
<p><strong>Member 1</strong></p>
</blockquote></th>
<th><blockquote>
<p><strong>Member 2</strong></p>
</blockquote></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><blockquote>
<p>Agent Design</p>
</blockquote></td>
<td><blockquote>
<p>Lead —</p>
<p>Orchestrat or &amp;</p>
<p>overall</p>
<p>architectu re</p>
</blockquote></td>
<td><blockquote>
<p>Lead — Specialized agent design</p>
</blockquote></td>
</tr>
<tr class="even">
<td><blockquote>
<p>Agent/Tool Development</p>
</blockquote></td>
<td><blockquote>
<p>Orchestrat or, Credit Agent,</p>
<p>database integratio n</p>
</blockquote></td>
<td><blockquote>
<p>Weather, Mandi,</p>
<p>Insurance agents &amp; API tools</p>
</blockquote></td>
</tr>
<tr class="odd">
<td><blockquote>
<p>Integration &amp; Testing</p>
</blockquote></td>
<td><blockquote>
<p>Lead — backend and multi-agent</p>
<p>integration</p>
</blockquote></td>
<td><blockquote>
<p>Lead — API testing,</p>
<p>UI testing and debugging</p>
</blockquote></td>
</tr>
</tbody>
</table>

<table>
<thead>
<tr class="header">
<th><blockquote>
<p><strong>Activity</strong></p>
</blockquote></th>
<th><blockquote>
<p><strong>Member 1</strong></p>
</blockquote></th>
<th><blockquote>
<p><strong>Member 2</strong></p>
</blockquote></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><blockquote>
<p>Evaluation &amp; Documentation</p>
</blockquote></td>
<td><blockquote>
<p>Evaluation methodol ogy &amp;</p>
<p>technical document ation</p>
</blockquote></td>
<td><blockquote>
<p>Test scenarios, results &amp; project</p>
<p>documentation</p>
</blockquote></td>
</tr>
<tr class="even">
<td><blockquote>
<p>Presentation/Interface UI</p>
</blockquote></td>
<td><blockquote>
<p>Backend integration with UI</p>
</blockquote></td>
<td><blockquote>
<p>Lead — React dashboard</p>
</blockquote></td>
</tr>
<tr class="odd">
<td><blockquote>
<p>Deployment</p>
</blockquote></td>
<td><blockquote>
<p>Lead —</p>
<p>backend/container setup</p>
</blockquote></td>
<td><blockquote>
<p>Support —</p>
<p>frontend/deployme nt testing</p>
</blockquote></td>
</tr>
</tbody>
</table>
