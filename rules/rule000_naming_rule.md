### Bxm Framework 특징
- SpringBoot framework을 기반으로 구성한 Application Framework임
- SpringBoot acthitecture를 준용한다.

### 2. **Spring Boot 특화 분석**
- `@Component`, `@Service`, `@Repository`, `@Controller`, `@RestController` 자동 감지
- `@Autowired`, Constructor/Setter/Field Injection 의존성 추적
- `@RequestMapping`, HTTP 메서드 기반 Endpoint 매핑

### 3. **BXM Framework 특화 annotaion **
- `@BxmCategory`: Bxm Framework에서 관리하는 컴포넌트 식별 annotaion
- `@BxmDataAccess`: Bxm Framwork 컴포넌트에서 Database access하기 위한 Datasource name
- `@BXMType` : Bxm Framework에서 사용하는 설명 코멘트
- `@BxmOmm_Field`: Bxm Framework의 DTO 필드 속성 표시
