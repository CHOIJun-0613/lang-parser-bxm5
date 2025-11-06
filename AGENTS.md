# CSA 프로젝트 에이전트 가이드

**중요**: 모든 대화는 공손한 어투의 한국어를 사용합니다.

## 1. 프로젝트 한눈에 보기
- **목표**: Spring Boot 기반 Java 애플리케이션을 정적 분석하여 코드 구조, Bean/엔드포인트 의존성, DB 연계를 Neo4j 그래프와 다양한 리포트로 제공합니다.
- **주요 산출물**: Neo4j 그래프 데이터, CRUD 매트릭스, DB 호출·영향도 리포트, Mermaid·PlantUML 시퀀스 다이어그램, 분석 통계 요약.
- **CLI 진입점**: `python -m csa.cli.main <command>` 형태의 Click 기반 CLI를 사용합니다.
- **분석 제외 디렉터리**: 숨김 폴더(이름이 `.`으로 시작), `commands`, `logs`, `neo4j`, `src`, `target_src`는 스캔 대상에서 제외합니다.
- **다이어그램 렌더링**: `libs/plantuml.jar`를 사용하여 PlantUML/시퀀스 다이어그램을 이미지로 변환합니다.

## 2. 핵심 모듈 지도
- `csa/cli/main.py`: CLI 엔트리포인트로, analyze·sequence·crud·db-analysis·impact·graph query·ai-enrich·class-spec 명령을 등록합니다.
- `csa/cli/commands/`: 각 명령의 옵션과 실행 절차를 정의합니다. `graph_queries.py`는 Cypher 실행을, `impact.py`는 영향도 리포트를, `ai_enrich.py`는 AI 보강 파이프라인을 담당합니다.
- `csa/cli/core/`: 공통 라이프사이클(`with_command_lifecycle`)과 실행 메타데이터 저장을 제공합니다.
- `csa/services/analysis/`: 분석 오케스트레이션. `handlers.py`가 Neo4j 초기화와 파이프라인 호출을 담당하며, `java_pipeline.py`는 배치/스트리밍 모드를 전환하고, `db_pipeline.py`는 DDL 디렉터리를 순회합니다. `neo4j_writer.py`는 그래프 적재 및 통계를 계산합니다.
- `csa/services/java_analysis/`: Java 트리 파싱 및 프레임워크 인식. `project.py`가 전체 AST를 구축하고, `spring.py`, `mybatis.py`, `jpa.py`, `tests.py`가 어노테이션과 SQL/테스트를 추적합니다. `bean_dependency_resolver.py`는 Neo4j 데이터를 기반으로 Bean 의존관계를 복원합니다.
- `csa/services/db_call_analysis/`: Neo4j에 저장된 Method↔SQL 관계로 CRUD 매트릭스(`crud.py`), 영향도 리포트(`impact_reporter.py`, `reverse_impact.py`), 호출 체인 다이어그램(`diagrams.py`)을 생성합니다.
- `csa/services/graph_db/`: GraphDB 파사드. `project_nodes.py`, `persistence_nodes.py`, `database_nodes.py`, `analytics.py`, `maintenance.py`가 프로젝트/애플리케이션/DB/분석/유지보수 믹스를 제공합니다.
- `csa/services/class_spec/`: 분석 결과를 기반으로 클래스 명세서를 생성(`generator.py`)하고 템플릿(`template.py`)을 관리합니다.
- `csa/aiwork/`: AI 분석/보강 엔진. `ai_analyzer.py`가 LLM 호출을 조율하고, `ai_providers.py`와 `ai_config.py`가 Google/Groq/LM Studio/OpenAI 등 프로바이더 설정을 추상화합니다.
- `csa/dbwork/connection_pool.py`: Neo4j 드라이버 커넥션 풀을 관리하여 CLI 종료 시 안전하게 반환합니다.
- `csa/diagrams/`: `sequence`와 `impact` 하위 모듈이 Mermaid/PlantUML 다이어그램을 생성하고 파일로 내보냅니다.
- `csa/parsers/`: 공통 파서 베이스(`base.py`)와 Java·DB·SQL 전용 파서를 제공합니다. Java 파서는 내부 클래스, Lombok, DTO 스킵 규칙 등을 지원합니다.
- `csa/models/`: `analysis.py`의 Pydantic 통계 모델과 `graph_entities.py`의 Neo4j 노드 모델을 정의합니다.
- `csa/utils/`: 로거(`logger.py`), 프로젝트 통계(`project_statistics.py`), LOC/복잡도 계산기, 규칙 매니저(`rules_manager.py`) 등 유틸리티를 포함합니다.
- `rules/`: 프로젝트 규칙과 정책을 정의하며, CLI 초기화 시 `rules_manager`가 로드합니다.
- `docs/`: 분석 기준 및 절차 문서(예: `SQL 복잡도 산정 기준(2025-11-06).md`)가 위치합니다.
- `tests/`: `unit`, `integration`, `contract` 테스트와 샘플 Spring 프로젝트(`tests/sample_*`)를 제공합니다.

## 3. 분석 파이프라인 흐름
1. **옵션 처리**: `validate_analyze_options()`로 실행 모드를 판별하고 `JAVA_SOURCE_FOLDER`, `DB_SCRIPT_FOLDER` 등을 확인합니다.
2. **Neo4j 준비**: `GraphDB` 인스턴스를 생성하고 `ensure_indexes()`로 MERGE 성능을 확보합니다. `--clean`과 `--java-object`, `--db-object`, `--all-objects` 조합에 따라 기존 노드를 정리합니다.
3. **DB 분석(선택)**: `analyze_full_project_db()`가 DDL 디렉터리를 순회해 Database/Table/Column/Constraint/Index 노드를 Neo4j에 적재합니다.
4. **Java 분석**  
   - *배치 모드*: `parse_java_project_full()`이 전체 소스 트리를 탐색해 패키지, 클래스, Bean, 엔드포인트, Mapper, JPA 엔티티, SQL을 수집합니다.  
   - *스트리밍 모드*: `parse_java_project_streaming()`이 파일 단위로 Neo4j를 갱신하여 메모리 사용량을 줄입니다. `USE_STREAMING_PARSE=true`일 때 활성화됩니다.
5. **Neo4j 저장**: `save_java_objects_to_neo4j()`가 프로젝트/패키지/클래스/메서드/Bean/SQL 노드를 생성하고 통계를 계산합니다.
6. **후처리**: `resolve_bean_dependencies_from_neo4j()`가 Bean 의존성을 보강하고, `print_analysis_summary()`가 실행 시간과 건수를 요약합니다.
7. **로그 관리**: 명령 실행 직전에 `set_command_context()`를 호출하면 `logs/{command}-YYYYMMDD.log`가 생성되고 7일 이전 로그가 정리됩니다.

## 4. 주요 CLI 명령
- `analyze`: Java/DB 전체 혹은 특정 객체를 분석합니다. `--java-object`, `--db-object`, `--all-objects`, `--class-name`, `--update`, `--dry-run`, `--db-script-folder`를 지원합니다.
- `crud matrix` 계열: 테이블/클래스 기준 CRUD 매트릭스와 교차표를 출력합니다.
- `db-analysis`, `db-statistics`, `db-call-chain`, `db-call-diagram`: Method↔SQL 관계를 바탕으로 통계, 호출 체인, 다이어그램을 생성합니다.
- `sequence`: Mermaid/PlantUML 포맷의 시퀀스 다이어그램을 생성하고 필요 시 이미지로 변환합니다.
- `impact`: 영향도 리포트, 역방향 영향도, 임팩트 다이어그램을 제공합니다.
- `graph query`: 기본/상세/상속/패키지 쿼리 혹은 사용자 정의 Cypher를 실행합니다.
- `ai-enrich`: `USE_AI_ANALYSIS=true`일 때 활성화되며, 분석 결과를 AI 요약/보강합니다.
- `class-spec`: 분석된 클래스 스펙을 템플릿으로 렌더링하고 파일로 저장합니다.

## 5. 데이터 모델 및 저장소
- **통계 모델**: `JavaAnalysisStats`, `DatabaseAnalysisStats`, `AnalysisResult`가 분석 결과를 구조화합니다.
- **그래프 엔티티**: `Project`, `Package`, `Class`, `Method`, `Field`, `Bean`, `Endpoint`, `SqlStatement` 등 노드 모델이 `graph_entities.py`에 정의됩니다.
- **GraphDB 믹스인**:  
  - `ProjectMixin`: 프로젝트/패키지/클래스 노드 생성 및 병렬 삽입  
  - `PersistenceMixin`: Bean·Endpoint·Mapper·JPA 엔티티·SQL 저장  
  - `DatabaseMixin`: Database/Table/Column/Index/Constraint 노드 관리  
  - `AnalyticsMixin`: SQL 통계, 테이블 사용량, 복잡도 분석 쿼리 제공  
  - `MaintenanceMixin`: 노드 정리와 관계 재구성 API 제공
- **커넥션 관리**: `csa/dbwork/connection_pool.py`가 Neo4j 세션 풀을 재사용하여 CLI 종료 시 안전하게 정리합니다.
- **출력 경로**: `.env`의 `SEQUENCE_DIAGRAM_OUTPUT_DIR`, `CRUD_MATRIX_OUTPUT_DIR`, `CLASS_SPEC_OUTPUT_DIR`, `IMPACT_ANALYSIS_OUTPUT_DIR` 설정에 따라 산출물이 저장됩니다.

## 6. 작업 절차 체크리스트
1. `.venv`를 활성화하고 `pip install -r requirements.txt`로 의존성을 설치합니다.
2. `.env`를 `env.example`에서 복사해 수정하고, Neo4j 접속 정보(`NEO4J_URI`, `NEO4J_DATABASE`, `NEO4J_USER`, `NEO4J_PASSWORD`)와 `JAVA_SOURCE_FOLDER`, 필요 시 `DB_SCRIPT_FOLDER`를 설정합니다.
3. 대규모 프로젝트라면 `USE_STREAMING_PARSE=true`를 유지하고, DTO 소스 제외(`SKIP_DTO_SOURCE`, `SKIP_DTO_METHODS`) 여부를 상황에 맞게 조정합니다.
4. 권장 실행: `python -m csa.cli.main analyze --all-objects --clean --project-name <별칭>`  
   기존 데이터를 보존하려면 `--clean`을 생략하거나 다른 프로젝트명을 사용합니다.
5. 분석 후 필요에 따라 `crud matrix`, `db-call-chain`, `sequence`, `impact` 명령으로 후속 리포트를 생성합니다.
6. 실행 로그는 `logs/{command}-YYYYMMDD.log`에 쌓이므로 문제 발생 시 이 파일을 확인합니다.

## 7. 테스트와 문서
- 테스트는 `pytest`로 실행하며, `tests/unit`, `tests/integration`, `tests/contract`로 구성되어 있습니다.
- `tests/sample_*` 디렉터리에 Spring 샘플 프로젝트와 계약 테스트용 자원이 포함되어 있습니다.
- 복잡도/통계 산정 기준과 운영 절차는 `docs/` 폴더의 Markdown 문서에서 확인할 수 있습니다. (예: `docs/SQL 복잡도 산정 기준(2025-11-06).md`)

## 8. 베스트 프랙티스 및 주의사항
- 스트리밍 모드(`USE_STREAMING_PARSE=true`)는 대규모 프로젝트에서 메모리 사용을 줄이지만 Neo4j 연결이 필수입니다.
- DTO 소스/메서드 스킵 옵션은 분석 속도를 높이지만 세부 코드 탐색이 필요한 경우 해제해야 합니다.
- 기존 Neo4j 데이터를 유지하려면 `--clean`을 사용하지 않고 프로젝트명을 구분하십시오.
- `USE_AI_ANALYSIS=true`일 때만 AI 보강 기능이 동작하며, 프로바이더 키는 로컬 환경 변수로 관리하고 저장소에 커밋하지 않습니다.
- `logs/`와 분석 산출물은 `.gitignore`에 포함되어 있으므로 공유용 파일은 별도로 복사해 관리합니다.
- 명령 실행 중 예상치 못한 변경이 감지되면 즉시 사용자에게 확인한 뒤 진행합니다.
