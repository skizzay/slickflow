# Build Java bytecode on the builder host; the final JRE follows --platform.
ARG BUILD_PLATFORM=linux/amd64
FROM --platform=${BUILD_PLATFORM} maven:3.9.9-eclipse-temurin-21@sha256:3a4ab3276a087bf276f79cae96b1af04f53731bec53fb2e651aca79e4b10211e AS build
WORKDIR /build
COPY pom.xml ./
COPY control-plane/pom.xml control-plane/pom.xml
COPY control-plane/src control-plane/src
RUN mvn -B -DskipTests package

FROM eclipse-temurin:21-jre-noble@sha256:0eda5830ed7b669abc246a8dc520ea8a23cab06f9a8d4b6964109e2f2394e46f AS base
ARG SOURCE_REVISION
LABEL org.opencontainers.image.source="https://github.com/skizzay/slickflow" \
      org.opencontainers.image.revision="${SOURCE_REVISION}"
WORKDIR /app
USER 10001:10001

FROM base AS migration
COPY --from=build /build/control-plane/target/control-plane-0.1.0-SNAPSHOT-migrate.jar /app/migrate.jar
ENTRYPOINT ["java", "-jar", "/app/migrate.jar"]

FROM base AS runtime
COPY --from=build /build/control-plane/target/control-plane-0.1.0-SNAPSHOT.jar /app/runtime.jar
# Container network binding only; the operator controls host publication.
ENV SERVER_ADDRESS=0.0.0.0
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/runtime.jar"]
