# Bob build tool
# Copyright (C) 2026  Bob Contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""SBOM (Software Bill of Materials) generation plugin."""

import re
from bob import BOB_VERSION
from bob.audit import Audit, Artifact
from bob.errors import BobError, BuildError, ParseError
from bob.input import Step, PluginSetting
from bob.intermediate import StepIR
from bob.scm import UrlScm

from dataclasses import dataclass
from datetime import datetime, timezone

import argparse
import gzip
import io
import json
import os

@dataclass
class SBOMGeneratorConfig:
    """Configuration of the Generator."""
    pretty: bool
    fileComponents: list[str]

@dataclass
class ArtifactInfo:
    """Common artifact properties needed by all SBOM Generators."""
    name: str
    package: str
    build_date: str
    cpe: str
    files: dict
    scms: dict
    variant_id: str
    description: str
    license: str
    vendor: str
    version: str
    bom_ref : str

    def __init__(self):
        pass

class SBOMGeneratorBase:
    """Base class for SBOM format generators."""

    def __init__(self, step: Step, config: SBOMGeneratorConfig):
        """Initialize SBOM generator with audit trail. """
        self._config = config
        self._step = step
        self._graph = {}

        auditFile = os.path.join(os.path.dirname(step.getWorkspacePath()), "audit.json.gz")
        try:
            self._audit = Audit.fromFile(auditFile)
        except Exception as e:
            raise BobError(f"Failed to load audit file: {e}")

        # create a mapping of variantIds to artifactIds. From the (dependencies) of our step we
        # only get variantIds but we have to look them up in the audit using artifactIds.
        self._variant_to_artifactId = self._get_variant_to_artifact_id_map()

    def _get_variant_to_artifact_id_map(self):
        artifacts = {}
        queue = [None]
        visited = set()

        while queue:
            aid = queue.pop(0)
            if aid in visited:
                continue
            visited.add(aid)

            art = self._audit.getArtifact(aid)

            artifacts[bytes.fromhex(art.getVariantId())] = aid
            for ref in art.getReferences():
                if ref not in visited:
                    queue.append(ref)

        return artifacts

    @staticmethod
    def _shorten_package_name(name: str):
        if not name:
            return 'unknown'
        if '::' in name:
            name = name.split('::')[-1]
        if '/' in name:
            name = name.split('/')[-1]
        return name

    @staticmethod
    def append_if_set(info : ArtifactInfo, name, info_name=None):
        val = getattr(info, info_name if info_name else name)
        if val is not None:
            return { name: val}
        return {}

    def generate(self):
        """Generate SBOM in the specific format.

        Returns:
            dict: SBOM data structure (format-specific)
        """
        raise NotImplementedError("Subclasses must implement generate()")

    def _generateSbomInfos(self, step, rootBomRef=None, processed=[], deployed={}):
        vid = step.getVariantId()

        if vid in processed:
            return None
        processed.append(vid)

        deps = []

        if not vid in self._variant_to_artifactId:
            raise BuildError(f"Can not get audit information for {step.getPackage().getName()}: "
                f"Expected Variant ID {vid.hex()} not found in audit. "
                "Different build or non matching arguments (--sandbox,..)?")
        artifact = self._audit.getArtifact(self._variant_to_artifactId[vid])

        audit_files = artifact.getFiles()
        next_deployed = deployed.copy()
        if 'sbom_deploy' in audit_files:
            try:
                sbom_deploy = json.loads(audit_files.get('sbom_deploy'))
            except json.JSONDecodeError as e:
                raise BuildError(f"Unable to load 'sbom_deploy' from audit of "
                    f"{step.getPackage().getName()}: {e}"
                    f"{audit_files.get('sbom_deploy')}")
            # sbom_deploy: list of dictionaries with "bob:sbom-manifest-id":"<id>, "files": [..]
            # only the via 'bob:sbom-manifest-id' referenced components are of interest for a deployed-sbom,
            # any other component is assumed to be not deployed
            for e in sbom_deploy:
                next_deployed[bytes.fromhex(e['bob:sbom-manifest-id'])] = e['files'] if 'files' in e else []

        data = None
        if step.isPackageStep():
            data = {'info': self._get_artifact_info(artifact, step),
                    'deployed' : deployed}
            if rootBomRef is not None:
                self._graph[rootBomRef].append(data['info'].bom_ref)
            self._graph[data['info'].bom_ref] = []
            rootBomRef = data['info'].bom_ref

        for dep in step.getArguments():
            if dep.isValid():
                depVariant = dep.getVariantId()
                deps.append(depVariant)
                yield from self._generateSbomInfos(dep, rootBomRef, processed, next_deployed)

        yield data


    def _get_artifact_info(self, artifact : Artifact, step : StepIR) -> ArtifactInfo:
        """Extract common artifact information from audit and step information."""
        info = ArtifactInfo()

        meta_data = artifact.getMetaData()
        meta_env = artifact.getMetaEnv()
        build_info = artifact.getBuildInfo()
        name = SBOMGeneratorBase._shorten_package_name(meta_data.get('package'))

        cpe_type    = meta_env.get('PKG_CPE_TYPE','a')
        cpe_vendor  = meta_env.get('PKG_CPE_VENDOR','*')
        cpe_product = meta_env.get('PKG_CPE_PRODUCT',
                                   SBOMGeneratorBase._shorten_package_name(meta_data.get('recipe')))
        cpe_version = meta_env.get('PKG_VERSION','*')
        cpe_update  = meta_env.get('PKG_CPE_UPDATE','*')
        cpe_edition = meta_env.get('PKG_CPE_EDITION','*')
        cpe_lang    = meta_env.get('PKG_CPE_LANG','*')
        cpe_sw_edition = meta_env.get('PKG_CPE_SW_EDITION','*')
        cpe_target_sw = meta_env.get('PKG_CPE_TARGET_SW','*')
        cpe_target_hw = meta_env.get('PKG_CPE_TARGET_HW','*')
        cpe_other     = meta_env.get('PKG_CPE_OTHER','*')

        cpe = f"cpe:2.3:{cpe_type}:{cpe_vendor}:{cpe_product}:{cpe_version}:{cpe_update}:{cpe_edition}:{cpe_lang}:{cpe_sw_edition}:{cpe_target_sw}:{cpe_target_hw}:{cpe_other}"

        info.build_date = build_info.get('date', '')
        info.cpe = cpe
        info.files = artifact.getFiles()
        info.name = name
        info.package = meta_data.get('package')
        info.scms = step.getPackage().getCheckoutStep().getScmList()

        info.description = meta_env.get('PKG_DESCRIPTION')
        info.license = meta_env.get('PKG_LICENSE')
        info.variant_id = artifact.getVariantId()
        info.vendor = meta_env.get('PKG_VENDOR')
        info.version = meta_env.get('PKG_VERSION')

        info.bom_ref = f"pkg:{info.name}:{info.variant_id}" + (f"@{info.version}" \
                           if info.version is not None else "")
        return info

class CycloneDXGenerator(SBOMGeneratorBase):
    """CycloneDX JSON format SBOM generator."""

    def generate(self):
        """Generate SBOM in CycloneDX JSON format."""

        processed = []
        components = []
        metadata = {}
        file_deps = []
        for data in self._generateSbomInfos(self._step, None, processed):
            if data is None:
                continue
            artifact = data['info']
            deployed = data['deployed']
            if bytes.fromhex(artifact.variant_id) == self._step.getVariantId():
                metadata = self._generate_metadata(artifact)
                continue # do not add the root element as component as this is in `metadata`
            component, component_file_deps = self._generate_component(artifact, deployed)
            components.extend(component)
            if len(component_file_deps) > 0:
                file_deps.append(component_file_deps)

        deps = self._generate_dependencies(file_deps)
        sbom = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.6",
            "version": 1,
            "metadata": metadata,
            "components": components,
            "dependencies": deps
        }

        return sbom

    def __add_external_references(self, data, info):
       data['externalReferences'] = [ {
               "type": "build-system",
               "url": "https://bobbuildtool.dev/"
           }]

       for scm in info.scms:
           data['externalReferences'].append({
                "type": "vcs",
                "url": scm.getProperties(False).get('url')
            })

    def _generate_metadata(self, info: ArtifactInfo):
        """Generate CycloneDX metadata."""
        now = datetime.now(timezone.utc)
        timestamp = now.replace(
            microsecond=0).isoformat().replace('+00:00', 'Z')
        metadata = {
            "timestamp": timestamp,
            "tools": [
                {
                    "vendor": "BobBuildTool",
                    "name": "bob sbom",
                    "version": BOB_VERSION,
                }
            ],
            "component": {
                "type": "application",
                "bom-ref": info.bom_ref,
                "name": info.name,
            } | SBOMGeneratorBase.append_if_set(info, 'version') \
              | SBOMGeneratorBase.append_if_set(info, 'description') \
              | SBOMGeneratorBase.append_if_set(info, 'cpe') \
              | CycloneDXGenerator._generate_licenses (info)
        }

        return metadata

    def _generate_component(self, info: ArtifactInfo, deployed):
        """Generate CycloneDX component"""
        file_deps = {}

        components = []

        audit_files = info.files
        component_bom_ref = info.bom_ref
        component_file_deps = []

        for f in self._config.fileComponents:
            if f in audit_files:
                try:
                    additional_sbom = json.loads(audit_files.get(f))
                    manifest_id = additional_sbom['bob:sbom-manifest-id']
                    filter = None

                    # if there is a deployment filter active but the actual package is not part of than it's not deployed
                    if len(deployed) > 0:
                        if bytes.fromhex(manifest_id) not in deployed:
                            continue
                        filter = deployed[bytes.fromhex(manifest_id)]

                    for c in additional_sbom["file_components"]:
                        # skip files if they are not in the deployment
                        if filter is not None and not c['name'] in filter:
                            continue
                        file_ref = f"file:{info.name}:{info.variant_id}:{c.get('name')}"
                        c.update({"bom-ref" : file_ref})
                        components.append(c)
                        component_file_deps.append(file_ref)
                except json.JSONDecodeError as e:
                    raise BuildError(f"Unable to load {f} from audit of {info.name}: {e}\n{audit_files.get(f)}")

        if len(component_file_deps) > 0:
            file_deps[component_bom_ref] = component_file_deps

        component = {
            "type": "application",
            "bom-ref": component_bom_ref,
            "name": info.name,
            "cpe": info.cpe,
            "externalReferences": []
        } | SBOMGeneratorBase.append_if_set(info, 'version') \
          | CycloneDXGenerator._generate_licenses(info)

        self.__add_external_references(component, info)

        components.append(component)

        return components, file_deps

    def _generate_dependencies(self, file_deps):
        """ Build the the dependency graph for pkgs and file dependencies. """
        dependencies = {}

        for root,deps in self._graph.items():
            dependencies[root] = deps

        for file_dep in file_deps:
            for root,deps in file_dep.items():
                if dependencies[root] is not None:
                    dependencies[root].extend(deps)
                else:
                    dependencies[root] = deps

        return [{'ref' : r, 'dependsOn' : d } for r,d in dependencies.items() if len(d) > 0 ]

    @staticmethod
    def _generate_licenses(artifact_info: ArtifactInfo):
        """Generate CycloneDX license information."""
        if artifact_info.license:
            if len(artifact_info.license.split()) > 1 or \
                artifact_info.license.startswith("LicenseRef"): # FIXME: Move all dependency license refs to the root dist
                # so we can import them as '{'license': {'text': {'content': "..."}}}
                # more than one word -> assume SPDX License Expression
                lic = {"expression": artifact_info.license}
            else:

                lic = {"license": { "id": artifact_info.license }}
            return {"licenses": [ lic ]}
        return {}

def sbomGenerator(package, argv, extra, bob):
    parser = argparse.ArgumentParser(prog="bob project sbom", description='Generate a SBOM')
    parser.add_argument('--pretty', action='store_true', default=False, help="Generaty pretty printed json output")
    parser.add_argument('--file-components', action='append', default=[],
                        help="Use file-component information from FILE_COMPONENTS of audit")
    parser.add_argument("-o", "--output", default="bom.json", type=str,
                        help="Name of output (json) file")

    args = parser.parse_args(argv)

    config = SBOMGeneratorConfig(args.pretty, args.file_components)

    generator = CycloneDXGenerator(package.getPackageStep(), config)
    sbom = generator.generate()

    dump_args = {}
    if config.pretty:
        dump_args['indent']=2
        dump_args['sort_keys']=True

    try:
        with open(args.output, 'w') as fp:
            json.dump(sbom, fp, **dump_args)
    except IOError as e:
        raise BobError(f"Failed to write output file: {e}")

    print(f"SBOM written to {args.output}")
    return 0;

manifest = {
    'apiVersion' : '1.2',
    'projectGenerators' : {
        'sbom' : sbomGenerator
    }
}
