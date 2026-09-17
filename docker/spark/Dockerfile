FROM apache/spark:3.5.9-java17-python3

USER root

# Versions des connecteurs (Spark 3.5 / Scala 2.12 / Hadoop 3.3.4)
ARG ICEBERG_VERSION=1.9.2
ARG PG_JDBC_VERSION=42.7.4
ARG HADOOP_AWS_VERSION=3.3.4
ARG AWS_SDK_BUNDLE_VERSION=1.12.262
ARG MAVEN=https://repo1.maven.org/maven2

# Iceberg (tables), S3FileIO, lecture s3a:// du bronze, écriture JDBC PostgreSQL
ADD ${MAVEN}/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/${ICEBERG_VERSION}/iceberg-spark-runtime-3.5_2.12-${ICEBERG_VERSION}.jar /opt/spark/jars/
ADD ${MAVEN}/org/apache/iceberg/iceberg-aws-bundle/${ICEBERG_VERSION}/iceberg-aws-bundle-${ICEBERG_VERSION}.jar /opt/spark/jars/
ADD ${MAVEN}/org/apache/hadoop/hadoop-aws/${HADOOP_AWS_VERSION}/hadoop-aws-${HADOOP_AWS_VERSION}.jar /opt/spark/jars/
ADD ${MAVEN}/com/amazonaws/aws-java-sdk-bundle/${AWS_SDK_BUNDLE_VERSION}/aws-java-sdk-bundle-${AWS_SDK_BUNDLE_VERSION}.jar /opt/spark/jars/
ADD ${MAVEN}/org/postgresql/postgresql/${PG_JDBC_VERSION}/postgresql-${PG_JDBC_VERSION}.jar /opt/spark/jars/
RUN chmod 644 /opt/spark/jars/*.jar

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY spark-defaults.conf /opt/spark/conf/spark-defaults.conf

ENV PYTHONPATH=/opt/homepedia/src \
    SPARK_NO_DAEMONIZE=true
WORKDIR /opt/homepedia
USER spark
