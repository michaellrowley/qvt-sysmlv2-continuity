FROM maven:3.9-eclipse-temurin-17 AS build

WORKDIR /workspace
COPY pom.xml ./
COPY scripts ./scripts
COPY src ./src
COPY qvt ./qvt
COPY examples ./examples

RUN scripts/download-qvt-libs.sh && mvn test package

FROM eclipse-temurin:17-jre

WORKDIR /app
COPY --from=build /workspace/target/sysml-v2-qvt-continuity-1.0.0-SNAPSHOT.jar /app/app.jar
COPY --from=build /workspace/examples /app/examples
COPY --from=build /workspace/qvt /app/qvt

ENTRYPOINT ["java", "-jar", "/app/app.jar", "lsp"]
