"""
Project 통계 집계 유틸리티 모듈

프로젝트의 파일 수, LOC 통계를 집계합니다.
"""

import os
from typing import Dict, List, TYPE_CHECKING
from csa.models.graph_entities import Class, Project

if TYPE_CHECKING:
    from csa.services.graph_db import GraphDB


def calculate_project_statistics(
    project: Project,
    classes: Dict[str, Class],
    java_source_folder: str
) -> Project:
    """
    프로젝트의 파일 통계와 LOC 통계를 계산하여 Project 객체를 업데이트합니다.

    Args:
        project: Project 객체
        classes: 파싱된 Class 객체들의 딕셔너리 (key: 클래스명)
        java_source_folder: Java 소스 폴더 경로

    Returns:
        Project: 통계가 업데이트된 Project 객체
    """
    from csa.utils.logger import get_logger
    logger = get_logger(__name__)

    logger.debug(f"calculate_project_statistics 호출: classes 수={len(classes)}, java_source_folder={java_source_folder}")

    # 파일 수 집계
    total_file_count = 0
    total_java_file_count = 0
    total_xml_file_count = 0
    total_etc_file_count = 0

    if java_source_folder and os.path.exists(java_source_folder):
        logger.debug(f"파일 시스템 순회 시작: {java_source_folder}")
        for root, dirs, files in os.walk(java_source_folder):
            # 제외할 디렉터리 건너뛰기
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', 'build', 'target', 'dist')]

            for file in files:
                # 숨김 파일 제외
                if file.startswith('.'):
                    continue

                total_file_count += 1

                if file.endswith('.java'):
                    total_java_file_count += 1
                elif file.endswith('.xml') or file.endswith('.dbio'):
                    # MyBatis Mapper 파일(.dbio)도 XML 파일로 간주
                    total_xml_file_count += 1
                else:
                    total_etc_file_count += 1

        logger.debug(f"파일 집계 완료: 전체={total_file_count}, Java={total_java_file_count}, XML={total_xml_file_count}, 기타={total_etc_file_count}")
    else:
        logger.warning(f"Java 소스 폴더가 존재하지 않음: {java_source_folder}")

    # LOC 통계 집계 (Java 파일만)
    total_ploc = 0
    total_lloc = 0
    total_cloc = 0

    for class_name, class_obj in classes.items():
        if class_obj:
            ploc = getattr(class_obj, 'PLOC', 0)
            lloc = getattr(class_obj, 'LLOC', 0)
            cloc = getattr(class_obj, 'CLOC', 0)
            total_ploc += ploc
            total_lloc += lloc
            total_cloc += cloc

    logger.debug(f"LOC 집계 완료: PLOC={total_ploc}, LLOC={total_lloc}, CLOC={total_cloc}")

    # Project 객체 업데이트
    project.total_file_count = total_file_count
    project.total_java_file_count = total_java_file_count
    project.total_xml_file_count = total_xml_file_count
    project.total_etc_file_count = total_etc_file_count
    project.total_PLOC = total_ploc
    project.total_LLOC = total_lloc
    project.total_CLOC = total_cloc

    # 기존의 number_of_files도 업데이트 (하위 호환성)
    project.number_of_files = total_java_file_count

    return project


def calculate_project_statistics_from_neo4j(
    db: 'GraphDB',
    project: Project,
    project_name: str,
    java_source_folder: str
) -> Project:
    """
    Neo4j에서 모든 Class 노드를 조회하여 프로젝트 통계를 계산합니다.
    --update 모드에서 사용됩니다.

    Args:
        db: GraphDB 인스턴스
        project: Project 객체
        project_name: 프로젝트명
        java_source_folder: Java 소스 폴더 경로

    Returns:
        Project: 통계가 업데이트된 Project 객체
    """
    # 파일 수 집계 (파일 시스템 기준)
    total_file_count = 0
    total_java_file_count = 0
    total_xml_file_count = 0
    total_etc_file_count = 0

    if java_source_folder and os.path.exists(java_source_folder):
        for root, dirs, files in os.walk(java_source_folder):
            # 제외할 디렉터리 건너뛰기
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', 'build', 'target', 'dist')]

            for file in files:
                # 숨김 파일 제외
                if file.startswith('.'):
                    continue

                total_file_count += 1

                if file.endswith('.java'):
                    total_java_file_count += 1
                elif file.endswith('.xml') or file.endswith('.dbio'):
                    # MyBatis Mapper 파일(.dbio)도 XML 파일로 간주
                    total_xml_file_count += 1
                else:
                    total_etc_file_count += 1

    # LOC 통계 집계 (Neo4j에서 모든 Class 조회)
    total_ploc = 0
    total_lloc = 0
    total_cloc = 0

    try:
        # Neo4j에서 프로젝트에 속한 모든 Class의 LOC를 조회
        loc_stats = db.get_project_loc_statistics(project_name)
        total_ploc = loc_stats.get('total_ploc', 0)
        total_lloc = loc_stats.get('total_lloc', 0)
        total_cloc = loc_stats.get('total_cloc', 0)

    except Exception as e:
        # Neo4j 조회 실패 시 0으로 유지
        pass

    # Project 객체 업데이트
    project.total_file_count = total_file_count
    project.total_java_file_count = total_java_file_count
    project.total_xml_file_count = total_xml_file_count
    project.total_etc_file_count = total_etc_file_count
    project.total_PLOC = total_ploc
    project.total_LLOC = total_lloc
    project.total_CLOC = total_cloc

    # 기존의 number_of_files도 업데이트 (하위 호환성)
    project.number_of_files = total_java_file_count

    return project


def aggregate_file_statistics(root_folder: str) -> Dict[str, int]:
    """
    폴더를 순회하며 파일 통계를 집계합니다.

    Args:
        root_folder: 루트 폴더 경로

    Returns:
        Dict[str, int]: 파일 통계 딕셔너리
            - total_files: 전체 파일 수
            - java_files: Java 파일 수
            - xml_files: XML 파일 수
            - etc_files: 기타 파일 수
    """
    stats = {
        'total_files': 0,
        'java_files': 0,
        'xml_files': 0,
        'etc_files': 0
    }

    if not root_folder or not os.path.exists(root_folder):
        return stats

    for root, dirs, files in os.walk(root_folder):
        # 제외할 디렉터리 건너뛰기
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in (
            'node_modules', 'build', 'target', 'dist', '__pycache__', 'venv', '.venv'
        )]

        for file in files:
            # 숨김 파일 제외
            if file.startswith('.'):
                continue

            stats['total_files'] += 1

            if file.endswith('.java'):
                stats['java_files'] += 1
            elif file.endswith('.xml'):
                stats['xml_files'] += 1
            else:
                stats['etc_files'] += 1

    return stats
