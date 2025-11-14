# bp charter tools

Favorite: No
Status: Inbox
Created: November 9, 2025
Edited: November 13, 2025 11:25 AM
Archive: No
Pin: No

## Docs

[Blue Planet Orchestration_ Administrator Guide - BPO_Administrator_Guide_2404_Issue_1-3.pdf](bp%20charter%20tools/Blue_Planet_Orchestration__Administrator_Guide_-_BPO_Administrator_Guide_2404_Issue_1-3.pdf)

[https://www.notion.so](https://www.notion.so)

### Container/solution mgmt in bp

## Quick Reference: **Blue Planet Platform Microservices**

Here're some quick references from Blue Planet Platform Microservices:

- **asset-manager**: Version control software and interface to Git
- **apigw**: Used to create, publish and maintain APIs.
- **BP-nagios**: Alerting and monitoring tool used to monitor Blue Planet microservices.
- **Bpocore**: Intent resource type repository and internal resource provider.
- **chronos**: Scheduler that provides a means for other microservices to delay an action.
- **datomic**: Distributed database, data stored as immutable facts and good at modeling complex relationships.
- **drools**: Stateful Policy Management engine.
- **elasticsearch**: Distributed search and analytics engine.
- **galera**: SQL database, used by several microservices to store data that does not need to be scaled.
- **nfv**: Network Function Virtualization engine.
- **camunda**: Business Process Modeling and Notation engine.
- **kibana**: Logs data Visualization plugin for Elasticsearch
- **heka**: Stream processing s/w used for parsing log files.
- **heroic**: Time-series database/repository that consumes metrics via Kafka.
- **kafka**: Software Messaging bus.
- **kibana**: Data visualization plugin for elasticsearch.
- **graphite**: Contains graphite time-series database and Grafana dashboard tool.
- **nrpe**: Remotely executes Nagios plugin on other hosts.
- **nagios**: Monitoring of microservice, network, hosts and infrastructure.
- **pm**: Orchestrates collection of metrics from resources.
- **postgresSQL**: SQL database.
- **scriptplan**: App in a Python virtual environment for Remote scripts execution.
- **solutionmanager**: BP internally developed container manager.
- **swagger-ui**: Provides access to APIs for testing and modeling.
- **Ractrl**: Provides a protocol for exchanging data with RA and aggregates all the RAs installed.
- **tron**: Centralized User Access Control system.

## Blue Planet Docker Network

Docker
 is used to package, distribute, and manage the various microservices 
that make up the Blue Planet software suite. This allows for a highly 
modular and scalable system where individual components can be updated, 
replaced, or scaled independently of one another.

Docker Network 
enables the containers to communicate with each other and with other 
networks. Docker provides various networking models such as bridge 
networks for isolated networks on a single host, and overlay networks 
for connecting multiple Docker daemons.

*Watch the following video to understand the functioning of Docker Network in Blue Planet.*

![image.png](bp%20charter%20tools/image.png)

![image.png](bp%20charter%20tools/image%201.png)

### kafka

## 

## Kafka and ZooKeeper

![](https://learning.ciena.com/pluginfile.php/140075/mod_scorm/content/3/scormcontent/assets/111_NOPROCESS_.png)

- Apache Kafka is a distributed event streaming platform.
- The role of Kafka in BPO MDSO is to provide a persisted event log
abstraction; like other enterprise messaging systems, producers publish
events to named topics and consumers consume these events by named
topics.
- Kafka feature of log compaction provides for smooth
shedding of stale history, ensuring that asymptomatically the log size
is proportional to the number of unique object IDs.
- ZooKeeper is a centralized service for maintaining configuration information, naming and distributed synchronization.

Here's how Kafka and ZooKeeper contribute to the various features:

- **High Availability:** Kafka uses replication to ensure high availability. Data is replicated across multiple brokers in a Kafka cluster, meaning that even if one broker
goes down, the data is still available from the other brokers. This
ensures continuous data availability and prevents data loss. Whereas
ZooKeeper provides a reliable, highly available and fault-tolerant
coordination service for distributed applications. It maintains an
active server list and, in case of failure, will redirect requests to
another server. This ensures that the system remains available even in
case of server failures.
- **Troubleshooting:** Kafka provides detailed logs and metrics which can be used for
troubleshooting. It also has a built-in feature to handle failures,
which can help in identifying and resolving issues. ZooKeeper also
provides detailed logs and can be configured to provide audit logs as
well. It also has built-in mechanisms for failure detection and
recovery, which can aid in troubleshooting.
- **Policy management:** Kafka allows for granular access control policies, ensuring secure data
access. Also, Kafka's quota feature allows for managing the resource
usage of each client, thereby ensuring efficient resource management.
ZooKeeper provides features for managing session timeouts, which can be
used to control resource usage.
- 

Here are the key takeaways from this section:

- 
- Container technology uses host OS features to provide an isolated environment for the applications to run on the same hardware server.
- 
- Blue Planet solutions are based on microservices implemented as Docker containers.
- 
- BP uses a custom bridge network named bp-bridge to facilitate connectivity between microservices.
- 

Container logs are kept in one place by way of persistent container volumes in the /opt/ciena/bp2 directory.

## more solman

Additional content has been loaded

Solution Manager

Top of page

[Blue Planet Orchestration Server Administration](https://learning.ciena.com/pluginfile.php/140075/mod_scorm/content/3/scormcontent/index.html#/)

17% COMPLETE

1. 
2. 

[1 of 6 — Container Management](https://learning.ciena.com/pluginfile.php/140075/mod_scorm/content/3/scormcontent/index.html#/lessons/ug-fscPDYvgx0V9_CJDd9zgNUjKqEvCN)

Lesson content**Solution Manager**Lesson 2 of 6
**Introduction**
The
 Solution Manager is a tool that helps in managing the lifecycle of 
network services. It provides end-to-end service orchestration and 
automation, enabling businesses to design, create, and deliver services 
across physical and virtual domains. This includes network and service 
inventory management, service order management, and service assurance. 
The Solution Manager aids in reducing operational complexity, 
accelerating service delivery, and improving operational efficiencies.

![](https://learning.ciena.com/pluginfile.php/140075/mod_scorm/content/3/scormcontent/assets/Optical_Backup_A.jpg.jpg)

![](https://learning.ciena.com/pluginfile.php/140075/mod_scorm/content/3/scormcontent/assets/13_NOPROCESS_.png)

- Solution Manager is configured to run with a Docker registry.
- It provides an HTTP API and the "Solman" Command Line Interface (CLI) for user interaction.
- It provides service discovery to allow various microservices to work together.
    - It connects service providers and consumers.
    - It facilitates app Clustering.
    - Each Blue Planet application can define a set of interfaces that they
    provide and consume with the other Blue Planet application.
        - The interface that an app provides to other Blue Planet applications is called NorthBound Interface (NBI),
        - The interface that an app consumes is called SouthBound Interface (SBI).

*Watch the following video to understand Solution Manager and the use specific commands to deploy, undeploy, backup, or restore the solution.*

![](https://learning.ciena.com/pluginfile.php/140075/mod_scorm/content/3/scormcontent/assets/BPO101_M1_Solution%20Manager_v2.0.jpg)

*Click each tab to learn more about the commands you can use effectively while working with the BPO microservices.*

## 

## 

## 

## 

## **Directory Structure**

Solution Manager manages a directory structure within each application container.

- The structure is mapped directly to /bp2 directory on the container file system.
    - host: **/opt/ciena/bp2/<container_name>/** >> container: **/bp2**
- Persistent subdirectories per container:
    - **data**: Keeps microservice data.
    - **log**: Application logs for the application.
    - **start_config**: Starting microservice configuration.
    - **tmp**: Temporary directory.
    - **src**: Source directory (some containers).
- **/opt/ciena/bp2** on the host is persisted across upgrades.

![](https://learning.ciena.com/pluginfile.php/140075/mod_scorm/content/3/scormcontent/assets/18_NOPROCESS_.png)

Solution
 Manager ensures high availability and continuity of service, minimizing
 the impact of system failures on the business operations.

Here's a general outline of how a Solution Manager redundancy and failover process work:

## 

## 

Must pass quiz before continuing: "Knowledge Check"

## redudancy

![image.png](bp%20charter%20tools/image%202.png)

![image.png](bp%20charter%20tools/image%203.png)

## SSL

# Secure Sockets Layer (SSL) Certificate Management

Lesson 3 of 6

![](https://learning.ciena.com/pluginfile.php/140075/mod_scorm/content/3/scormcontent/assets/BP_Abstract_F.jpg.jpg)

**Public Key Infrastructure**

## **Cryptography**

Cryptography
 is a method of protecting information by transforming it into an 
unreadable format. It is a method of storing and transmitting data in a 
particular form so that only those for whom it is intended can read and 
process it.

The main task of cryptography is to protect 
information. It keeps communication and information between end systems 
secret by encrypting it. It allows only the sender and intended 
recipient of data to view its contents.

![](https://learning.ciena.com/pluginfile.php/140075/mod_scorm/content/3/scormcontent/assets/26_NOPROCESS_.png)

Cryptography provides the following important services:

- **Confidentiality**: protects against eavesdropping, no system in between the two entities should be able to decrypt the communication.
- **Authentication**: assures the identity of the entities is legitimate.
- **Integrity**: protects against the alteration of the messages between the entities.

## **Introduction to Public Key Infrastructure (PKI)**

Public
 Key Infrastructure (PKI), is a set of roles, policies, and procedures 
needed to create, manage, distribute, use, store, and revoke digital 
certificates and manage public-key encryption. It is a system for the 
creation, storing, and distribution of digital certificates which are 
used to verify that a particular public key belongs to a certain 
entity.

![](https://learning.ciena.com/pluginfile.php/140075/mod_scorm/content/3/scormcontent/assets/27_01_NOPROCESS_.png)

**Digital Certificates**

- A digital certificate contains a public key and the identity of the owner.
- X.509 is an ITU standard for the format of public key certificates.

![](https://learning.ciena.com/pluginfile.php/140075/mod_scorm/content/3/scormcontent/assets/27_02_NOPROCESS_.png)

**Certificate Authority (CA)**

- Entity that signs and issues digital certificates.

## **Public and Private Keys Concept**

![](https://learning.ciena.com/pluginfile.php/140075/mod_scorm/content/3/scormcontent/assets/28_NOPROCESS_.png)

The server creates a set of keys before they are used in communication.

- A public key is distributed freely.
    - Used to encrypt messages.
- A private key should be kept very secure.
    - Used to decrypt messages.

Messages encrypted with a server’s public key can only be decrypted with the corresponding private key.

- For some algorithms (for example, RSA) this also works in reverse, messages encrypted with the private key can be decrypted with the public key – **which provides proof of identity**.

## **Certificate Authority (CA)**

- A CA acts as a trusted third party between two entities:
    - A server (for example, a web server) and a client (for example, a web browser).
- The primary role of the CA is to digitally sign and publish the public key bound to a given subject.
    - Signed using the CA's own private key.
    - Trust in the user key relies on the trust in the validity of the CA's key.
- Implementation of CA depends on the use case.
    - **Public CAs**: public, mainly paid service.
        - IdenTrust, DigiCert, Let’s Encrypt, AWS, GCP
    - **Private CAs**: deployed on private infrastructure.
        - Private Linux server running openssl.
        - Has no significance outside of the enterprise.
        - Typically self-signed.
        - Open-source software, free.

![](https://learning.ciena.com/pluginfile.php/140075/mod_scorm/content/3/scormcontent/assets/29_NOPROCESS_.png)

## **Signing a Public Key Certificate**

- CA uses its own private key to sign the subject’s public key.
    - This validates that CA signed it.
- Trust in the user key relies on validity and trust in the CA's key.
    - If you don’t trust the CA itself, then you don’t trust the certificates it signs down the line.

![](https://learning.ciena.com/pluginfile.php/140075/mod_scorm/content/3/scormcontent/assets/30_NOPROCESS_.png)

## BPO Orchestration Arch: Messaging service

### Messaging Service

In this topic, we will discuss the means by which the applications 
within Blue Planet communicate. Obviously, it important that the myriad 
of components that make up the Blue Planet infrastructure are able to 
interact. To provide this capability the Blue Planet Orchestrate 
includes as part of its architecture an open source messaging service 
application known as Kafka. Kafka is a streaming platform that handles 
the exchange of data amongst applications and solutions. So what exactly
 is a messaging service and how does it work?

The messaging service is organized around producers, consumers and 
topics. An application will register with Kafka as a producer and/or 
consumer of messages on a particular topic. A topic is a category to 
which a stream of records are published. Each topic can have any number 
of consumers subscribed to the data that gets published to it. Each 
topic is maintained as a partitioned log which a sequence of records 
that are continually being appended. A producer application will update a
 topic with a specific set of data called an envelope which includes a 
description of the event, a timestamp, user information and identifiers 
to correlate events with other requests or events. The term envelope is 
appropriate as this acts in much the same manner as a post office box in
 which a letter is left in the box until its owner can retrieve it.

Kafka will retain the published records for a configurable retention 
period. In that sense Kafka is kind of a storage system. The topic in 
messaging bus is available to the consumer application who can read and 
respond to this event when it is free to do so. The producer application
 will not be forced to wait for a response because its message has been 
delivered. This avoids latency within Blue Planet and the message will 
not be lost in the event of a catastrophic failure of a node within the 
server cluster.

A message can be set up in two ways: queues or topics. The difference
 between the two is in how messaged get delivered to the registered 
consumers. When a publisher sends messages to a queue destination, each 
message will go to the first consumer who consumes it and only to that 
consumer. Which consumer receives the message is not defined. Messages 
sent to a queue are persistent and if no consumers are registered to the
 queue at the time it is sent it will be delivered to consumers that 
register with the queue in the future.

When load balancing is important the queue format is used. When an 
application needs to send events to be processed by some other part of 
the system, Queues allows those events to be processed by any one of the
 modules subscribing to the queue, effectively load balancing the 
events.

When a consumer sends a message to a topic destination, the message 
will be received by all the consumers registered to the topic. Consumers
 that register to the topic after the message has been sent will not 
receive these messages. Topics are used when you want to publish message
 to notify other modules about state changes.

Let’s look at an example. In certain instances, a Resource Provider 
will use a Kafka topic during discovery of domain resources.  When a RA 
want to inform Blue Planet about changes in its Domain, it will place 
this event notification on a Kafka topic. The application within Blue 
Planet responsible for managing the Resource Adaptors has registered as a
 consumer of this topic to monitor for any changes to the domain. This 
consumer application picks up the message from the topic which, 
depending on the content of the message, may kick off a series of events
 to update the Market with any changes to the domain.

In this lesson we covered

Blue Planet’s utilization of the Kafka messaging service

The concept of queues and topics as they a

## Market Catalogs

### Market Catalogs

You will see the market metaphor throughout this lesson. Names such as
    Market, Product and Catalog are no accident. Resource Providers add
    descriptions of their Products, or offerings, to the Market. They are made
    available, or advertised, via a product catalog. Those Products are
    available for consumption by customers of Blue Planet. Customers in this
    case may be the any or anything that can access the Market through it’s
    APIs. For instance, some services or resources may be instantiated by an
    operator/administrator but they could also be instantiated network
    management system for an automated service. This lesson will examine the
    Market component within the Blue Planet architecture along with the
    definition files and templates that are required to model the elements and
    services of the orchestrated domains.

Upon completion of this lesson you will:

· Be able to Identify the objects maintained in each of the Market
    catalogs.

· Be familiar with the APIs exposed by Market

· Understand the role of Resource Type and Service Template definition
    files

Blue Planet models the orchestrated world as sets of objects and the Market
    component is responsible for storing, maintaining, updating and providing
    access to those objects. The individual elements within orchestrated
    domains, services that use those elements and the relationships that define
    how the elements interact are all represented as objects. The Market stores
    the objects in three layered catalogs. The Market also exposes a set of
    APIs that are used to query and update the Market database. This includes
    APIs to work with the Resources, Type definitions, relationships, products,
    resource providers and domains. We will display the list contained within
    each of the sets throughout this lesson.

An object in this case is a structured set of data that define a set of
    attributes that describe something. The Resource objects, model entities
    from different domains. Shown here is the how one resource, in this case a
    Juniper Network Function, is represented in Blue Planet. All Resources are
    built from a common base schema; however, the properties for a resource are
    specific to the Resource Type. The contents of the Properties attribute is
    determined by the developer of the Resource Type that the Resource is
    created from.

This, like most objects in Blue Planet, is represented in the JSON Format
    and based on a JSON-Schema. If you are unfamiliar with JSON, it is a data
    format that consist of name/value pairs. It is a way to store information
    in an organized, easy-to-access manner. The schema defines what attributes
    can or need to be included and the format they need be in (string, number
    etc.). Adhering to a schema is important because Blue Planet, and any
    software for that matter, needs the data it consumes to be in a format it
    can work with and understand.

The three layered catalogs in Market are Type, Product and Instance. The
    Type catalog contains, among other things, descriptions of all Resource and
    Relationship types. The Product catalog contains the objects that link the
    Resources to their Domains and exposes the availability of the Resources to
    the end-users. The instances catalog tracks the resources and relationships
    that have been realized.

When a Resource Adaptor is deployed, it will first onboard its Resource
    Types and Products via the Asset Manager. If the onboarding is successful
    it will be registered with the Market as the Resource Provider or RP for
    that Resource Adaptor. The Market will create an object in the Instance
    Catalog that contains the necessary data about the RP. A unique id is
    created for the RP which can then be used by other components to address it
    for the purpose of discovering or modifying the resources within the RP’s
    domain. In this way, changes in the domain will create a modification to
    the Market database. Pictured here is a Resource Provider object queried
    from the Market that shows the attributes associated with the RP schema.
    These are values that were defined within the Resource Adaptor. Though not
    shown here, the resourceTypes attribute will contain a list of all of the
    Resource Types and their attributes that the RP has provided. The APIs
    exposed by the Market related to Resource Providers enable external users
    of the Market to create, update and delete Resource Providers in the
    Market. It is worth noting that these APIs are not used frequently as
    Resource Providers are usually added via an interaction between external
    Resource Providers and the RA Manager.

Once onboarded, Market will add the Types to the Type Catalog. Blue Planet
    will then contain a model of what is available and what can be managed
    within the Domain as defined in the Resource Adaptor.

When a Domain is created in Blue Planet, the Market will already know what
    it can offer since the types have already been provided. At this time, a
    new Domain object will be created with a unique domain id and the Products
    for the Resource Types defined for the Domain will be added to the Product
    Catalog. Blue Planet now needs to know which Resource instances exist in
    the Domain. To find out, Market will request the Resource Provider to sync
    with the domain. The Resource Provider will then inform the Market as to
    which and how many of each type are active. Market will then update the
    instance catalog by creating new instance objects. The Market exposes a set
    of APIs that provide the ability query, add, remove or update the Domains.

Let’s take a look at the market catalogs, beginning with the instance
    catalog. The instance catalog maintains a record of instantiated resources
    within the domains. When a product is instantiated an instance of the
    Resource Type the product represents is created. In Blue Planet instances
    are referred to as simply Resources. Not all Resource instances can be
    managed by Blue Planet but it needs to know about the orchestration states
    of all Resource in order to provide an accurate model of the Domains. The
    instance catalog maintains a record of the Resource objects throughout
    their lifecycle.

The Instance Catalog can be viewed as a graph database. A graph database is
    designed to treat the relationships between elements as first-class
    objects. That is the are treated in much the same way as other objects.
    This allows for simple and fast retrieval of complex structures that are
    difficult to model. It consists of nodes that represent entities within a
    domain and edges that represent relationships among these entities. As an
    example, a graph database that maintains employee data would represent an
    employee as a node, or object, that contains the property values unique to
    the employee. The employee is connected to a company also represented by an
    object. They are connected with a relationship object that contains its own
    set of properties. This aligns with the model of Resources and
    Relationships employed by Blue Planet. For example, a domain that offers
    network services may contain virtual local area network object that have a
    dependency of a Virtual Machine. The two objects are linked together with a
    dependsOn relationship object.

There are three types of Resources maintained in the instance catalog:
    External, Composite and Built-in.

External Resources have a direct one-to-one relationship with a logical or
    physical entity in one of the orchestrated Domains. Examples of this Type
    are Network Elements, physical port, termination point, or virtual machine.
    External Resources are always tied to an external Domain and mediated via a
    Resource Provider.

Composite resources are aggregation of built-in, external and/or other
    Composite Resources. No one-to-on relationship exist for a composite
    Resource. It is a construct that only exists in inside Blue Planet.
    Composite Resources are implemented by a Service Template that defines the
    necessary sub-resources, relationships and lifecycle instructions. A
    typical use of a Composite Resource would be the implementation of an
    end-to-end service that required multiple virtual or physical devices
    across multiple domains. Composite Resource are onboarded through the asset
    manager manually and are not provided by a Resource Provider. As such they
    are implemented and managed by Blue Planet’s internal Resource Provider and
    Template Engine.

Built-in Resources are provided and managed by Blue Planet. There is no
    direct relationship with an external source. Instead they are provided by
    Blue Planet’s internal Resource Provider. These are Resource that are
    useful as building blocks for composite resources. A few examples of the
    built-in resources are Number Pool used to manage a poof of continuous
    range of integers, IPV4AddressPool to manage a pool of IPv4 address or
    Monitor which is used to monitor the Kafka messaging bus.

Managed Resources are added to the Instance Catalog when they are
    instantiated through their Products. The Resource is assigned a
    orchestration state of activating and a call is sent to the Provider of the
    Resource to create the update the Domain. The Market will wait to be
    informed that the Resource was successfully created before changing its
    orchestration state to active. If an error occurs the orchestration state
    will be set to failed. Instantiation of composite Resource is managed
    through the internal Template Engine. A composite Resource may require
    multiple sub-resource be activated. In this case the Template Engine will
    send the request to market for each sub-resource and market will create the
    instance as it does for any external Resource.

Pictured here is a resource object queried from the instance catalog. Every
    instance object is assigned a unique id and includes references to its
    product and resource type. The properties object contains a number of
    modifiers used to describe the Resource and its behaviors. When a
    modification is requested on a Resource, such as activate or terminate, the
    desiredorchstate will reflect that request. Once the modification has
    occurred it will be reflected in the orchState.

Just as Resources are active instance of Resource Types, Relationships are
    active instances of a Relationship Type. Relationships are expressed in
    terms of a source Resource and a Target Resource where the source Resource
    has a requirement and the target Resource has a capability that satisfies
    that requirement. The Relationship instance forms the link between the
    source and target Resource. Here you can see that the source and target are
    linked with the source’s id and requirement name with the target’s id and
    capability name. There several other attributes that can be applied to a
    Relationship though they may not be required. Pictured here is a
    relationship object and you can see that there are additional attributes
    that reference the relationship types and provider data which contains data
    controlled by the provider of the Relationship. Market exposes APIs to
    query, add and delete relationship instances.

The Type catalog contains the definitions of a number of artifact types.
    This include Resource Types, Relationship Types, Property Types and
    Capability Types. Types can be added to the catalog is extensible, that is
    types can be added or modified without interrupting any component in Blue
    Planet. This enables Blue Planet to be adaptive to multiple devices without
    the need for any software upgrades.

The objects in the Type Catalog are created by using definition files.
    These files are written in a structured format called HOCON, which is a
    format for human-readable data and a subset of JSON. Definition files
    contain the artifacts which define data models or behaviors. The artifacts
    include the properties, capabilities, requirements and other
    characteristics of Resource instances. These attributes allow the author of
    the definition file to specify how the properties can be configured in a
    format that can be consumed by Blue Planet.

Once the Market consumes the Resource Type definition files via the Asset
    Manager, it converts the data from the HOCON format to a JSON format, then
    validates this JSON object against a schema validator and compiles that
    into an internal object that represents the Resource. Active instances of
    the Resource Type can then be created from this object.

Displayed here is the view of one Resource Type object as it exists in the
    Type Catalog. You can see it contains the data in the definition file
    though the object shows all items from the schema.

The derivedFrom attribute that can be used to identify one or more resource
    types to inherit from. This allows the Resource Type to re-use the
    properties, capabilities and requirements that have already been defined in
    another Type. Developing Types in a manner in which they can be used to
    build on each other saves development time and makes updating easier since,
    when a type is edited, the changes will be reflected in all Types that have
    inherited its properties. When the inheriting Resource Type is instantiated
    Market will import the attributes and values from the types identified in
    the derivedFrom attribute.

Composite Resources Types that execute a service utilizing multiple
    Resource Types are defined the same way as other Resource Types. However,
    they also require a template, called Service Template, to implement it. A
    Service Template can be thought of as the recipe that identifies the
    required sub-resources and provides lifecycle instructions for the
    Composite Resource. A Service Template definition file will identify the
    resource type it is implementing. It contains a resource attribute in which
    all of the sub-resources are defined along with the specific behaviors and
    values it requires to achieve the service. Blue planet provides some
    specific language elements, called directives, which can be used to provide
    additional logic to the implementation.

The Relationship Type defines characteristics of Relationship Instances
    that are

specific to the type. Relationship Types are defined through definition
    files that include the schema of the Relationship’s properties attribute
    and the valid type of capability and requirement on the source and target
    Resource instances.

Blue Planet ships with the following Resource Types:

dependsOn: reccommeced base type for all relationship types

ConnectsTo: express a connection between resources

hostedOn: Rcpre]\

MadeOf: Express composition of sub-resources

The Capability Type defines categories of features which are provided or
    used by Resources. Defined through definition modules both Capabilities and
    Requirements defined on Resource Types are instances of Capability Types.
    Capability Types can be reused to avoid the overhead of defining a separate
    set of artifacts.

The Product catalog maintains the Product objects. All Resources Instances
    are based on Products. Each Product defines an offering of a Resource Type
    in a specific Domain. In this way a Product ties Resources to their
    corresponding Resource Types and provides a link between a Resource
    Instance and a Domain. Each Resource is linked to one Product and each
    product is linked to one Domain. Products are added to the Catalog when a
    Domain is added via the Products Resource Provider. The Products announce
    to the rest of the system that they are able to offer a particular
    Resource.

Products act as the primary basis for access control for resource creation.
    Authorization policies can be tied to product, controlling who can create
    what types of resources over what domains.

While Products are onboarded by their Resource Providers, they can also be
    added manually for Composite Resources by using the Product APIs exposed by
    Market.

In this lesson we covered:

· The role of the three catalogs in market.

- The APIs exposed by Market

· An overview of Resource Type and Service Template definition files

## Template Engine

Composite resources are implemented using Service Template definitions. The
    Service Template identifies the sub-resources, property values specific to
    the sub-resources and plans that define behaviors for lifecycle events. The
    Template Engine is responsible for composition of, and the lifecycle
    support for, Composite Resources as they are described in the Resource’s
    Service Template Definition.

In this lesson you learn to:

- Describe the purpose of the Template Engine

· Identify the three lifecycle operations supported by Blue Planet

· Describe the difference between declarative and imperative programming

· Describe implementation of declarative and imperative lifecycle
    operations

In general, a template engine is software designed to combine templates
    with a data model to produce result documents. For instance, a web template
    system will combine a number content resources such as data streams from a
    database, a web template and stylesheets into a single web document. Often
    template engines utilize Domain Specific Languages, or DSLs, which are a
    language or set of elements that can be used to reference a more complex
    set of functions. One example of a DSL is HTML made up of tag elements. A
    Web developer doesn’t need to worry about writing code to organize content
    into a paragraph, they simply use the P tag and the template engine, or in
    this case the browser, will handle the complexity of organizing the
    content.

The Blue Planet Template Engine composes composite resources by compiling
    attributes from Service Templates, resources type definitions and scripts.
    Service Templates developers can take advantages of a custom DSL provided
    by Blue Planet to more easily execute complex requirements.

While Resources are connected to an external domain, Composite Resources
    have no specific tie to any external resource but instead represent a
    logical construct that only exists in the Orchestrator. Because they are
    not tied to a specific Domain or Resource Adaptor they are in Blue Planet’s
    built-in Planet Orchestrate domain. The Template Engine acts as the
    Resource Provider for the built-in Domain and is responsible for realizing
    the life-cycle operations of Composite Resources.

Let’s take a look at what happens when a Composite Resource is
    instantiated. When a Composite Product is activated, the Template Engine is
    notified in the same way an external Resource Provider is notified when a
    product within its domain is invoked. Once notified, the Template Engine
    will begin to implement the lifecycle plan as described in the Product’s
    Service Template. It then requests the sub-resources that are defined in
    the Service Template, creates the connection between the resource and
    sub-resources and propagates updates from composite resource to
    sub-resources based on directives in the Service Template. The sub
    resources will either be provided by another composite resource via the
    built-in resource provider or a managed resource from a managed Domain.

Once the Composite Resource has been created, the Template Engine will
    support it for the remainder of its lifecycle. Usually one of three
    lifecycle operations are being implemented on a Resource: Activate, Update
    and Terminate. Like all Resources, Composite resources contain an attribute
    for desired orchestration state, or orchstate, and observed orchestration
    state. The Desired Orchestration State: indicates the desired lifecycle
    state as specified by the user. A desired orchestration state can be active
    to specify the Resource should be activated, or terminated to specify the
    Resource should be terminated. There is an additional state of unspecified
    but the unspecified state only applies to discovered resources and is not
    relevant here.

The Orchestration State specifies the observed lifecycle state of the
    Resource. The value of the orchState changes throughout the lifecycle and
    may transition through the states of requested, activating, active /
    failed, terminating and terminated as displayed in this diagram.

When a Resources is first created the desired orchstate defaults to active
    and the orchstate defaults to requested. The Template Engine monitors the
    orchestration state which is used to determine if a failure has occurred by
    comparing it to the desired state.

The process involved for the lifecycle operations are as follows:

**Activate**
    : Activation is the process of realizing Resources in managed domains. A
    simple case may only require a single API call to the domain or it may
    require creating multiple entities separate from the Resource. Some
    Resources may require additional steps to ensure that it arrives in an
    acceptable baseline state which is operational from an orchestration
    perspective. Once activation completes, it is considered active. What
    active means will vary among different resources. Some examples are:

A Virtual Machine is running and has a publicly accessible IP address.

A VPN service is provisioned and there is connectivity between sites.

For a composite resource managed by the Template Engine the process of
    activation will most likely involve the creation of multiple sub-resources.
    If the sub-resources originate from a managed Domain, the Template Engine
    will coordinate with the Resource Providers of that domains to instantiate
    those particular resources. When the Resource Provider receives a
    notification to activate a Resource it may set its orchState to
    “activating.” Upon completion of the activation process the Resource’s
    orchState will be changed to “Active”

**Update**
    : Update is the process of applying changes to configuration properties of
    a Resource that have been marked as updatable. Once the update has been
    initiated, the Resource’s desired orchestration state will change and there
    will be difference between the desired orchestration state and
    orchestration state. The Resource’s Resource Provider is notified and is
    then responsible for realizing the change in the Domain and to update the
    orchestration state. The update will be considered successful when the
    reality of the resource matches the desired orchestration state and the
    orchestration will be updated accordingly. If the Resource Provider cannot
    implement the change the Resource’s orchState will be set to failed.

**Terminate**
    : Termination if the process of undoing steps taken to realize the
    Resources in managed Domains. Upon initiating a delete operation, the
    desired orchestration property is set to “terminated’ and the Resource
    Provider is notified to take the appropriate action in the Domain. When the
    Resource Provider has completed the termination tasks the orchestration
    state is updated to terminated and the Resources will be removed from the
    instance catalog. If there are Resources that have a dependency
    relationship with the targeted Resource, that is the Resource we are trying
    to terminate, the termination of the targeted resource will fail. All
    dependent Resources must be terminated before the target Resource can be
    deleted.

Lifecycle operations are defined in the Service Template using either
    declarative programming or imperative programming.

The template engine supports a number of JSON directives available inside
    the template body to

manipulate data and to support more complex logic. These are conceptually
    function calls that can be

placed in places where otherwise a value is expected. Refer to the Service
    Template Directives reference

for more details.

In **Declarative programing**, you describe what you want done
    and not the sequence of steps necessary to get it done. It is often
    described as implying a description of what you want to get from an
    application and not its control flow. By employing a Domain Specific
    Language, declarative programming hides the lower layer of programming from
    the user. This provides a way for non-programmers to achieve results
    without going through the months or years learning to code.

~~HTML provides a good example of declarative programming since you are
        specifying what you want done not how to achieve it. For example to
        create an article with an image (the end result) requires the following
        HTML tags. The actual code to implement this on a web page is very
        complex and would take a great deal of time to write and execute. In
        addition, every programmer would write that code in a different way and~~

A Service Template specifies declarative instructions in its resources
    section using a DSL custom to Blue Planet. The DSL for Service Templates
    provide the building blocks to describe how a resource should be created
    and may define specific conditions or ordering.

Pictured here is a table of the available declarative directives. Each
    calls a set of functions within Blue Planet to implement some behavior. The
    terminate before directive specifies that the termination of a resource
    must be done before another. The join directive is used to glue various
    values into one string. The get attribute directive is used to fetch a
    property of one of the peer resources. The entire list of DSL attributes
    can be found in Blue Planet Developer Guide which you can access on the
    community website.

Let’s take a closer look at the get attribute directive. Employing the get
    attribute directive will call the code in Blue Planet that will return an
    attribute from a peer resource. In the example shown we are passing
    parameters to identify the peer resource we want to access (l2vpn) and
    which data element within the resource we want the value of (gwPortVlanId).
    This does require learning the directives and how to use them but compared
    to the complexity of the code required to implement this request shown on
    the right, it is relatively simple.

To further illustrate the concept of using declarative directives in
    activating a resource, let’s say we have a Composite Resource that requires
    the creation of three sub-resources resource A, resource B, and resource C,
    that have ordering dependencies. A declarative model could simply declare
    that resource B can be created only after A is complete, and C assumes that
    B is complete. This can be done by specifying the ordering of activation
    via the “activateAfter” attribute of the sub-resource in the Service
    Template. In this case we are using declarative programming to implement a
    sequential activation. If the resources do no depend on each other we could
    leave out the directives and resources would activate in parallel. In our
    the sequentia example we have identified dependencies between the resources
    and the template engine will create the relationships to reflect this.

During the termination process the Template Engine will generate a plan or
    a series of tasks to terminate the service. The tasks include terminating
    the sub-resources defined in the template and the relationship between the
    composite resource and sub-resources. The Template Engine will terminate
    the sub-resources in a parallel fashion unless the template includes
    terminateBefore directives to enforce a sequence.

Now this may seem complex but when compared to learning a whole programming
    language it is fairly simple. Programming languages provide some
    constraints but the implementations of how things are implemented will vary
    greatly from programmer to programmer, quality issues can arise and a great
    deal of time can be consumed. On the other hand, how declaratives are
    implemented will not change no matter how many developers may work on the
    service implementation. The declarative approach is the preferred way to
    implement your Service Template and should be used whenever possible.

When using **imperative programming** you are attempting to
    say how you want something done. This involves specifying the sequence of
    steps which must be executed in order to realize a service and requires
    know exactly how you want something done. If you were writing a programming
    to mimic driving a car from point a to point through you would include the
    following checks and statements shown here:

While Imperative programming is probably the most widely used paradigm in
    programming languages such as C++, Java, PHP and Python, it can become
    complex and requires a good deal of programming knowledge in order to
    achieve the desired results.

Though more complex than declarative directives, Imperative plans allow for
    greater flexibility in controlling how lifecycle operations are
    implemented.

To use imperative programming, you provide scripts that define plans to
    implement the Resources lifecycle operations. You identify the activate,
    terminate and update scripts in the plans section of the service template.
    scripts will always override declarative plans. When a lifecycle operation
    is requested, the Template Engine executes the appropriate imperative
    script. The Template Engine invokes the user defined code contained in the
    onboarded scripts to creating sub-resources, creating any relationships
    between the resources, propagating changes when the composite resource is
    update. Both the Template Engine and the imperative plan will provide the
    composite resource.

In this lesson we covered

- How the Template Engine provide Composite Resources
- The three lifecycle operations supported by Blue Planet

· The difference between declarative and imperative programming

· How to implement declarative and imperative lifecycle operations

## RA MANAGER

### RA Manager

In this topic we will cover the means by which Blue Planet discovers
    changes in the Domains it is orchestrating. Networks are living things that
    will grow and change over time. Elements within a managed domain may be
    updated, deleted added. Changes in the network that had not been initiated
    through Blue Planet will create a disparity between what exist in the
    Market catalog and the reality of the orchestrated domain. The component
    within Blue Planet that ensures any changes the occur in the Domain are
    reflected in the Market is the RA Manager.

Upon completion of this lesson you will be able to:

- Describe the purpose of the RA Manager Component

· Explain the means by which Blue Planet updates an Orchestrated Domain

· Identify and explain the discovery strategies used to monitor the
    Orchestrated domains

RA Manager is a set of classes within the Blue Planet that provides a
    protocol for exchanging data with the Resource Adapter and, therefore the
    domain. The RA Manager’s job is to act as an intermediary between the
    Market and the RA. This is enabled by REST APIs exposed by the Market and
    the southbound Resource Provider or RP.

We know that the Market provides a set of APIs and the RA Manager uses
    these APIs to query, update and delete records from the Market database.
    But how does the communication take place southbound, that is between RA
    Manager and the Resource Adapter? The answer to that is found in a
    component known as the RPSDK.

The RPSDK is a software library used for building Resource Providers that
    communicate with Blue Planet. To do this the RPSDK provides is a framework
    for implementing APIs that provide a gateway to the Resource Adapter.

The APIs exposed by the RP enable access to functions that:

- Create new domains
- Delete existing domains
- Return a list of products for a particular resource type
- Query a specific Resource Type
- Create a Resource within a
- Update a Resource
- Delete a Resource

At the time a Resource Adaptor is deployed in Blue Planet, it onboards its
    type definitions and registers itself as a Resource Provider. The Market
    will then maintain a unique identifier for the RP which the RA Manager will
    use to connect to the RP. The Resource Type definitions within the RA will
    be added to the Type Catalog. At this time the Products defined in the RA
    will not be added to the Market Catalog though RA Manager will maintain a
    record of them.

For each new domain added via the RP, the RA Manager will create the
    products in the Market Catalog and will associate them with the Domain.
    This association will allow user of these products to create Resources in
    this Domain. RA Manager will then begin to discover the Resource instances
    within the Domain.

Let’s examine the part RA Manager plays in the instantiation of a Resource.
    We will use the example of an end user selecting a product via the UI. This
    can be done via a direct API call, but for illustration purposes we are
    showing the UI. The Product is tied to a Resource Type which identifies the
    Resource’s properties, the properties types and any other Resources that
    may be required for instantiation. The user provides the required values or
    constraints and then on Create, an API call is sent to market and a
    Resource is created in Market.

Each Resource orchestration state is represented in a value called
    orchstate. When the Resource creation process first begins the orchstate is
    activating and it will remain so until it is determined whether the
    Resource has been created. Displayed here are the other orchstate values
    supported in Blue Planet.

The RA Manager is then responsible for communicating the request to the
    applicable Resource Provider and does so by sending a POST call to create a
    new Resource within the Domain. The protocols and commands required to do
    this are identified in the Resource Adaptor at the time it was developed
    and from here the RA that manage the process of creating the Resource. The
    RA then reports back to RA Manager if the Resource could be successfully
    instantiated.

RA Manager will then provide that information to Market and, if successful,
    the orchstate will be changed to active.

Composite Products, those that reference a Service Template are different
    because they are managed by an internal Resource Provider or template
    engine. When a Composite Product is activated, the Composite Resource is
    created in market and the Template Engine is notified. Once notified, the
    Template Engine will begin to implement the lifecycle plan as described in
    the Product’s Service Template. It will create the required sub-resources
    in Market. For resources that are managed by an RA, Market will have RA
    Manager create the Resources in the external domains and report back when
    or if the resource has been successfully completed.

Since the Product was not provided by a resource adapter it must be managed
    by an internal Resource Provider. The internal Resource Provider handles
    creating the resource in market and the another group of classes known as
    the Template Engine stitch toghether the sub-resources that make up the
    composite resource. Sub-Resources that exist in the external domains still

All Resources within Blue Planet are either discovered or not discovered.
    Resources are considered discovered when it is the Domain that reports its
    existence to Blue Planet. Discovered Resources cannot be removed or
    modified by Blue Planet. Resources that have been instantiated by Blue have
    a discovered state of false because they are managed by Blue Planet’s
    built-in Resource Provider not an external RA. However, the sub-resources
    that reside in the external Domains are most usually discovered Resources.

Why this matters here is that reporting to Market which resources are
    discovered is the job of the RA Manager.

There are two strategies for discovering Resources in the orchestrated
    Domains: Synchronous and Asynchronous. Which strategy is used is determined
    by the RA developer and identified in the RAs Resource Provider
    Configuration file.

*[file 11]*
    The difference between the two strategies is how the devices will be
    polled, that is how Blue Planet inquiries about the state of the Domain.
    When the synchronous type is used RA Manager will do periodic checks to
    determine whether there have been any changes that require an update to the
    Market database. If Asynchronous is used, RA Manager will do no polling and
    rely on the Resource Adapter to send asynchronous updates.

When an RA is set to use the the synchronous discovery strategy, RA Manager
    will periodically request a LIST of resources. There are two flavors of
    Synchronous strategy type: List-Only and Get-Only.

First let’s look at the List-Only strategy. The RA Manager will
    periodically send a GET request to return a list of active Resources for
    Resource Types in the RA. RA Manager then compares the list provided by the
    Domain against what it knows about the current state of the Market to
    determine whether something needs to be created, deleted or updated in the
    market. If something is missing in the list response, RA Manager will send
    a GET command on that specific resource and if it receives anything other
    than a 404-error code, an error code that indicates a client server was not
    able to communicate with another server, it will set the Resource’s
    orchstate to unknown state and wait for the next polling to resolve the
    issue. Otherwise the orchstate will be set to terminated and it will be
    removed from market if either: it's discovered state equals true, or it’s
    discovered state equals false and it’s desired orchstate is equals
    terminated.

The extra GET is designed so the resource would not be claimed terminated
    prematurely when there is a connectivity issue or other problem. This
behavior can be optionally turned off by setting the    **verifyMissingList** to false in the RP config YAML file for
    this type, so that a resource will be deemed terminated as soon as it is
    missing in the LIST.

When the GET-only strategy is used When the Get-only strategy is used the
    RA Manager will not issue a periodic LIST call to the RA. Instead it will
    issue GET calls to each resource of a specific type separately and if it
    receives a 404 error will delete the instance of that resource in the
    Market.

If the GET call returns a valid resource that is different from the
    corresponding entity in the Market database, the Market database will be
    updated based on the returned resource.

Since there is no LIST calls to the RA in this case, there is essentially
    no "discovery" done. In other words, the RA Manager only polls the
    resources it knows about, which are usually resources created from market.
    This could be useful if there are a potentially lot of resources of a type
    in the southbound but the orchestration workflow only cares about the
    resources created by the user directly or indirectly.

When the asynchronous strategy is used, the RA Manager is passively
    listening to the message bus topic for the RA to send an event to the topic
    and therefore may miss some events that occur if the RA has lost
    connectivity or has been restarted. If a resource has been deleted from the
    domain but not the market there is now discrepancy between Blue Planet and
    the Domain. The RA won’t be able to send a terminate event because it no
    longer knows about the resource so no evaluation with the Market takes
    place. In cases like this the RA Manager must resync with the Domain.

When an RP restarts it can initiate a resync event. The RP first sends
    start event along with the scope of the Resources being sent. This will be
    followed by events for all Resources within the Domain and a stop event
    once all Resources events have been sent. When RA Manager receives the stop
    event it compares the Resources to those, within the scope, in Market. If
    the Resource is in Market but had not been supplied in the events the
    Resources orchstate will be changed to “terminated.” After the resync
    process, the Market, RP and Domain should be aligned.

In this lesson we learned that

· The RA Manager is a set of classes that handles communication between the
    Market and Resource Providers.

· It provides the discovery of changes that have occurred within a Domain
    and then updates those changes to the Market.

· The RA Manager can discover those changes synchronously by continuous
    polling of a Resource Provider, or asynchronously, by registering with a
    messaging service topic and waiting to be informed of changes by the
    Resource Provider.

## Deployment model

![image.png](bp%20charter%20tools/image%204.png)

## more bp arch

- Solution is a set of applications that are deployed and managed as a single unit.
- Solution Manager facilitates the life-cycle collection of related microservices as a single solution.
- Part of the BP2 type deployments.
- Configured to run with a Docker registry.
- Provides an HTTP API and the "solman" CLI for user interaction.
- Provides service discovery to allow various microservices to work together.
    - Connects service providers and consumers.
    - Uses the following abstractions:
        - NorthBound Interfaces (NBIs)
        - SouthBound Interfaces (SBIs)
    - App Clustering
- Manages the solution life-cycle (deploy, un-deploy, upgrade, backup, restore, and so on).
- Provides system services for service discovery and clustering.
- Uses a "hook" based interface for communications to apps.

## **Solutions: Solution Data Image**

![](https://learning.ciena.com/pluginfile.php/136576/mod_scorm/content/2/scormcontent/assets/Kocaa34qWYUG8WiG_MQsPg3KRuXBIE4w4-26_NOPROCESS_.png)

## **Service Discovery**

![](https://learning.ciena.com/pluginfile.php/136576/mod_scorm/content/2/scormcontent/assets/8A6tfaGw6sDY0Vgw_s-ZLRx9PqC1gTt9_-27_NOPROCESS_.png)

| Container | 1 | 2 | 3 | 4 | 5 |  |
| --- | --- | --- | --- | --- | --- | --- |
| IPAddress | 172.16.0.41 | 172.16.0.47 | 172.16.0.56 | 172.16.0.48 | 172.16.0.32 | 172.16.0.28 |
| Capabilities | { } | { } | { } | { } | { } | { } |
| Dependencies | { } | { } | { } | { } | { } | { } |

## **Service Discovery: NBI / SBI**

![](https://learning.ciena.com/pluginfile.php/136576/mod_scorm/content/2/scormcontent/assets/YulIJF9zgDLpHBE-_7tuSIVy4w-XORXiw-28_NOPROCESS_.png)

| Container | 1 | 2 | 3 | 4 | 5 | 6 |
| --- | --- | --- | --- | --- | --- | --- |
| IPAddress | 172.16.0.41 | 172.16.0.47 | 172.16.0.56 | 172.16.0.48 | 172.16.0.32 | 172.16.0.28 |
| Capabilities | { } | { } | { } | { } | { } | { } |
| Dependencies | { } | { } | { } | { } | { } | { } |

## **Access Solution Manager CLI**

- **ssh into the server:**
    - ssh bpadmin@<Host IP>IPAddress is a placeholder for your specific Blue Planet instance.
- **Solman to Run Solution Manager:**
    - sudo solman

![](https://learning.ciena.com/pluginfile.php/136576/mod_scorm/content/2/scormcontent/assets/sGw87cxhq3_LjkKX_7-GcSH8EoXAH6O7q-29_NOPROCESS_.png)

## **Solution Manager – the Solman Utility**

**Show available commands:**

(cmd) help

**Provides list of deployed solutions:**

(cmd) sps

**View specific status of specific container:**

(cmd) sps | grep <container name>

![](https://learning.ciena.com/pluginfile.php/136576/mod_scorm/content/2/scormcontent/assets/i7f-p-0qCW23YTDQ_hSUFCvA5OJHBUYff-30_NOPROCESS_.png)

![](https://learning.ciena.com/pluginfile.php/136576/mod_scorm/content/2/scormcontent/assets/3rU9RZdJCX-w3yRa_JA5hm5dGVxlUoZKC.jpg)

**Key Takeaways**

Here are the key takeaways from this section:

- 
- BP2 is intended to support deployments with fixed size or "minimally sized" clusters.
- 
- K8s imperative is to move to the Cloud native architecture and support
Automated Rollouts, Rollbacks, Auto Scaling, and Self Healing.
- 
- Swagger is a server-side tool that can perform REST API calls on the server. It is used to demonstrate and develop API calls.
- 
- Solution Manager is a part of BP2 deployment model types and facilitates the
life-cycle collection (deploy, un-deploy, upgrade, backup, restore, and
so on) of related microservices as a single solution.
- 
- Solution Manager Provides an HTTP API and the "solman" CLI for user interaction.
- 

## **Blue Planet Centralized Logging**

![](https://learning.ciena.com/pluginfile.php/136576/mod_scorm/content/2/scormcontent/assets/DNnQ_okf6c9P2fCH_Dh1Wg4-GooUdAIYQ-31_NOPROCESS_.png)

**Centralized logging is a system which:**

- Aggregates all the logs from different hosts to a central location.
- Consolidates all the logs.
- Makes the data accessible through a single, easy-to-use interface.

**Centralized logging in Blue Planet consists of three tools:**

- Elasticsearch
- Fluentd / Heka
- Kibana

**Elasticsearch & Kibana**

- Elasticsearch is an open-source, broadly-distributable, readily-scalable, enterprise-grade search engine.
- Kibana is an open-source data visualization plugin for Elasticsearch.
- Both are accessed via one UI.
- Blue Planet Platform Administrators need to be able to use the features provided by Elasticsearch & Kibana to view logs.

![](https://learning.ciena.com/pluginfile.php/136576/mod_scorm/content/2/scormcontent/assets/x5cDEtZYzRISVFf0_W34QjnxJkY75F2TH-32_NOPROCESS_.png)

## **Blue Planet Logging Conventions**

- Each log message contains one or more fields.
    - Standard fields (see table later in this section).
    - Application specific fields (Custom fields).
- Fields are named with snake_case strings and are considered case-insensitive.
    - Applications must not emit fields named with an initial underscore.
    - Applications must not emit fields named with a period.
- Typically, field values should be:
    - String
    - Boolean
    - Integer
    - Double
- Null values typically represent existing fields that have dropped their values.
- Binary data is typically stored as an array of integers: [65, 32, 66].

![](https://learning.ciena.com/pluginfile.php/136576/mod_scorm/content/2/scormcontent/assets/PMaJeP3CWTkK4CBq_O4pTOvX0C7Yvr4g1-33_NOPROCESS_.png)

A priority is a numeric value used to indicate how serious a log message is.

Blue Planet follows the Linux conventional log priorities:

![](https://learning.ciena.com/pluginfile.php/136576/mod_scorm/content/2/scormcontent/assets/XNzReFiHALBzyW1H_wf4x7ckKbYkbClz6-34_NOPROCESS_.png)

## **Linux Administration Feature**

- System log files become very large over time.
- Logrotate is used to handle this potential issue:
    - Executed nightly through a cron job.
    - Designed to rotate log files.
    - Configured automatically with "CienaBundle”.
    - Configuration files:
        - /etc/logrotate.conf
        - /etc/logrotate.d

## 

## 

## 

## 

## 

## 

## 

## 

## 

## 

## 

## 

## 

## 

## 

## 

## 

## 

## Code

- 
    
    ```python
    Given your experience building the SEEFA observability platform with custom correlation engines, here's how you can create a parallel monitoring solution for MDSO:
    
    ## Architecture Patterns for Custom Observability
    
    ### 1. **Sidecar Proxy Pattern**
    Create microservices that act as monitoring sidecars:
    
    ```yaml
    # Docker Compose example for metric interceptor
    metric-forwarder:
      image: your-metric-proxy
      environment:
        - PROMETHEUS_ENDPOINT=http://mdso-prometheus:9090
        - CUSTOM_BACKEND=https://your-observability-platform
      volumes:
        - /var/run/docker.sock:/var/run/docker.sock
    ```
    
    ### 2. **Event Stream Tap Architecture**
    
    Build a multi-component solution:
    
    **Component A: Metric Exporter Service**
    ```python
    # Scrape Prometheus metrics and forward to your stack
    class MetricBridge:
        def __init__(self):
            self.prom_client = PrometheusClient('http://localhost:9090')
            self.custom_sink = YourObservabilityClient()
        
        def stream_metrics(self):
            # Query Prometheus API
            metrics = self.prom_client.query_range(
                'up{job=~"mdso.*"}',
                start_time='-5m'
            )
            # Transform and forward
            self.custom_sink.ingest(self.transform(metrics))
    ```
    
    **Component B: Log Aggregation Proxy**
    ```python
    # Elasticsearch log forwarder
    class LogForwarder:
        def __init__(self):
            self.es_client = Elasticsearch(['mdso-elasticsearch:9200'])
            self.custom_logger = CustomLogPlatform()
            
        def tail_logs(self):
            # Subscribe to ES indices
            for hit in helpers.scan(self.es_client, 
                                   index="mdso-*",
                                   query={"range": {"@timestamp": {"gte": "now-1m"}}}):
                self.custom_logger.ship(hit['_source'])
    ```
    
    ### 3. **API Gateway Instrumentation**
    
    Since MDSO uses REST APIs, implement an observability gateway:
    
    ```python
    from flask import Flask, request
    import requests
    
    app = Flask(__name__)
    
    @app.route('/api/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
    def proxy_with_telemetry(path):
        # Capture metrics
        start_time = time.time()
        
        # Forward to MDSO
        response = requests.request(
            method=request.method,
            url=f'http://mdso-internal/api/{path}',
            headers=request.headers,
            data=request.get_data()
        )
        
        # Send telemetry to your stack
        telemetry = {
            'endpoint': path,
            'method': request.method,
            'status': response.status_code,
            'latency': time.time() - start_time,
            'timestamp': datetime.utcnow()
        }
        
        send_to_custom_platform(telemetry)
        return response.content, response.status_code
    ```
    
    ### 4. **OpenTelemetry Integration Layer**
    
    Leverage OpenTelemetry for vendor-agnostic observability:
    
    ```yaml
    # otel-collector-config.yaml
    receivers:
      prometheus:
        config:
          scrape_configs:
            - job_name: 'mdso-metrics'
              static_configs:
                - targets: ['mdso-prometheus:9090']
      
      elasticsearch:
        endpoint: http://mdso-elasticsearch:9200
        indices: ["mdso-*"]
    
    exporters:
      your_custom_backend:
        endpoint: "https://your-observability.company.com"
        api_key: "${CUSTOM_API_KEY}"
    
    processors:
      batch:
      transform:
        metric_statements:
          - context: metric
            statements:
              - set(attributes["environment"], "mdso-production")
    
    service:
      pipelines:
        metrics:
          receivers: [prometheus]
          processors: [batch, transform]
          exporters: [your_custom_backend]
        logs:
          receivers: [elasticsearch]
          processors: [batch]
          exporters: [your_custom_backend]
    ```
    
    ### 5. **Database-Level Monitoring**
    
    Since MDSO uses PostgreSQL, implement WAL-based change data capture:
    
    ```python
    # PostgreSQL logical replication for audit
    class MdsoAuditStream:
        def __init__(self):
            self.pg_conn = psycopg2.connect(
                "host=mdso-postgres dbname=bpocore"
            )
            self.setup_replication_slot()
        
        def stream_changes(self):
            cur = self.pg_conn.cursor()
            cur.execute("SELECT * FROM pg_logical_slot_get_changes('mdso_audit', NULL, NULL)")
            for change in cur:
                self.process_audit_event(change)
    ```
    
    ## Implementation Strategy
    
    ### Phase 1: Read-Only Integration
    - Deploy metric scrapers as separate containers
    - Use Prometheus federation to pull metrics
    - Stream logs via Elasticsearch API
    
    ### Phase 2: Active Instrumentation  
    - Implement HTTP proxy for API monitoring
    - Add distributed tracing with OpenTelemetry
    - Create custom Resource Adapter for monitoring
    
    ### Phase 3: Full Replacement (If Needed)
    - Disable built-in monitoring via GCS settings
    - Replace with custom stack entirely
    - Maintain API compatibility for existing dashboards
    
    ## Deployment Configuration
    
    Add to your deployment:
    
    ```bash
    # Disable default monitoring (if allowed)
    docker exec mdso-solutionmanager \
      curl -X PUT http://localhost:8080/api/v1/gcs/settings \
      -d '{"monitoring.prometheus.enabled": false}'
    
    # Deploy your monitoring stack
    docker-compose -f monitoring-bridge.yml up -d
    ```
    
    Given your experience with the correlation engine and log aggregation for SEEFA, you could build a sophisticated bridge that maintains all MDSO's monitoring capabilities while feeding your preferred observability platform. The key is to treat the built-in stack as a data source rather than the final destination.
    
    Would you like me to elaborate on any specific integration pattern or help design the correlation logic between MDSO events and your custom monitoring stack?
    ```
    

## Reflections

`

[https://prod.liveshare.vsengsaas.visualstudio.com/join?148A867B5B22A88ED27D48134B871380CB38](https://prod.liveshare.vsengsaas.visualstudio.com/join?148A867B5B22A88ED27D48134B871380CB38)