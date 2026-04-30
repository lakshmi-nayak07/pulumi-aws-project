"""AWS Infrastructure with Pulumi"""
import pulumi
import pulumi_aws as aws

# ---------------------------
# Fetch latest Ubuntu AMI
# ---------------------------
ubuntu_ami = aws.ec2.get_ami(
    most_recent=True,
    owners=["099720109477"],
    filters=[
        aws.ec2.GetAmiFilterArgs(
            name="name",
            values=["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
        )
    ]
)

# ---------------------------
# VPC
# ---------------------------
vpc = aws.ec2.Vpc("dev-vpc",
    cidr_block="172.16.0.0/16",
    tags={"Name": "dev-vpc-pulumi"}
)

# ---------------------------
# Subnets
# ---------------------------
web_subnet = aws.ec2.Subnet("web-subnet",
    vpc_id=vpc.id,
    cidr_block="172.16.1.0/24",
    availability_zone="eu-north-1a",
    map_public_ip_on_launch=True,
    tags={"Name": "web-public-subnet"}
)

app_subnet = aws.ec2.Subnet("app-subnet",
    vpc_id=vpc.id,
    cidr_block="172.16.10.0/24",
    availability_zone="eu-north-1a",
    tags={"Name": "app-private-subnet"}
)

# ---------------------------
# Internet Gateway
# ---------------------------
igw = aws.ec2.InternetGateway("dev-igw",
    vpc_id=vpc.id,
    tags={"Name": "dev-igw"}
)

# ---------------------------
# Public Route Table
# ---------------------------
web_rt = aws.ec2.RouteTable("web-rt",
    vpc_id=vpc.id,
    routes=[
        aws.ec2.RouteTableRouteArgs(
            cidr_block="0.0.0.0/0",
            gateway_id=igw.id
        )
    ],
    tags={"Name": "web-route-table"}
)

# Associate public route table with web subnet
web_rt_assoc = aws.ec2.RouteTableAssociation("web-rt-assoc",
    subnet_id=web_subnet.id,
    route_table_id=web_rt.id
)

# ---------------------------
# Private Route Table
# ---------------------------
app_rt = aws.ec2.RouteTable("app-rt",
    vpc_id=vpc.id,
    tags={"Name": "app-route-table"}
)

app_rt_assoc = aws.ec2.RouteTableAssociation("app-rt-assoc",
    subnet_id=app_subnet.id,
    route_table_id=app_rt.id
)

# ---------------------------
# Get current public IP
# ---------------------------
my_ip = aws.get_caller_identity()

# ---------------------------
# Security Groups
# ---------------------------

# Web Security Group
web_sg = aws.ec2.SecurityGroup("web-sg",
    vpc_id=vpc.id,
    description="Web server security group",
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            from_port=22,
            to_port=22,
            protocol="tcp",
            cidr_blocks=["0.0.0.0/0"]  # restrict to your IP
        ),
        aws.ec2.SecurityGroupIngressArgs(
            from_port=80,
            to_port=80,
            protocol="tcp",
            cidr_blocks=["0.0.0.0/0"]
        )
    ],
    egress=[
        aws.ec2.SecurityGroupEgressArgs(
            from_port=0,
            to_port=0,
            protocol="-1",
            cidr_blocks=["0.0.0.0/0"]
        )
    ],
    tags={"Name": "web-sg"}
)

# App Security Group
app_sg = aws.ec2.SecurityGroup("app-sg",
    vpc_id=vpc.id,
    description="App server security group",
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            from_port=22,
            to_port=22,
            protocol="tcp",
            security_groups=[web_sg.id]
        )
    ],
    egress=[
        aws.ec2.SecurityGroupEgressArgs(
            from_port=0,
            to_port=0,
            protocol="-1",
            cidr_blocks=["0.0.0.0/0"]
        )
    ],
    tags={"Name": "app-sg"}
)

# ---------------------------
# Key Pair
# ---------------------------
key = aws.ec2.KeyPair("pulumi-key",
    key_name="pulumi-generated-key",
    public_key=open("pulumi-key.pub").read()
)

# ---------------------------
# EC2 Instances
# ---------------------------

# Web Server
web_server = aws.ec2.Instance("web-server",
    ami=ubuntu_ami.id,
    instance_type="t3.micro",
    subnet_id=web_subnet.id,
    key_name=key.key_name,
    vpc_security_group_ids=[web_sg.id],
    user_data="""#!/bin/bash
apt update -y
apt install -y apache2
systemctl start apache2
systemctl enable apache2
echo "Hello from Pulumi Web Server" > /var/www/html/index.html
""",
    tags={"Name": "web-ec2"}
)

# Web Server 2
web_server_2 = aws.ec2.Instance("web-server-2",
    ami=ubuntu_ami.id,
    instance_type="t3.micro",
    subnet_id=web_subnet.id,
    key_name=key.key_name,
    vpc_security_group_ids=[web_sg.id],
    user_data="""#!/bin/bash
apt update -y
apt install -y apache2
systemctl start apache2
systemctl enable apache2
echo "Hello from Pulumi Web Server 2" > /var/www/html/index.html
""",
    tags={"Name": "web-ec2-2"}
)

# App Server
app_server = aws.ec2.Instance("app-server",
    ami=ubuntu_ami.id,
    instance_type="t3.micro",
    subnet_id=app_subnet.id,
    key_name=key.key_name,
    vpc_security_group_ids=[app_sg.id],
    tags={"Name": "app-ec2"}
)

# ---------------------------
# Outputs
# ---------------------------
pulumi.export("web_server_public_ip", web_server.public_ip)
pulumi.export("web_server_2_public_ip", web_server_2.public_ip)
pulumi.export("app_server_private_ip", app_server.private_ip)
pulumi.export("vpc_id", vpc.id)