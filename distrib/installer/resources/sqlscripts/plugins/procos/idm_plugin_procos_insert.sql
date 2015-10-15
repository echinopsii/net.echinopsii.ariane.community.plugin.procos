--
-- Dumping data for table `resource`
--
LOCK TABLES `resource` WRITE;
INSERT IGNORE INTO `resource` (description, resourceName, version) VALUES
    ('Injector for mapping ProcOS','injMapSysProcOS',1);
UNLOCK TABLES;



--
-- Dumping data for table `permission`
--
LOCK TABLES `permission` WRITE,`resource` WRITE;
INSERT IGNORE INTO `permission` (description, permissionName, version, resource_id)
SELECT 'can display system mapping ProcOS injector', 'injMapSysProcOS:display', 1, id FROM resource WHERE resourceName='injMapSysProcOS';
INSERT IGNORE INTO `permission` (description, permissionName, version, resource_id)
SELECT 'can play action on system mapping ProcOS injector', 'injMapSysProcOS:action', 1, id FROM resource WHERE resourceName='injMapSysProcOS';
UNLOCK TABLES;



--
-- Dumping data for table `resource_permission`
--
LOCK TABLES `resource_permission` WRITE,`permission` AS p WRITE,`resource` AS r WRITE ;
INSERT IGNORE INTO `resource_permission` (resource_id, permissions_id)
SELECT r.id, p.id FROM resource AS r, permission AS p WHERE r.resourceName='injMapSysProcOS' AND p.permissionName='injMapSysProcOS:display';
INSERT IGNORE INTO `resource_permission` (resource_id, permissions_id)
SELECT r.id, p.id FROM resource AS r, permission AS p WHERE r.resourceName='injMapSysProcOS' AND p.permissionName='injMapSysProcOS:action';
UNLOCK TABLES;



--
-- Dumping data for table `permission_role`
--
LOCK TABLES `permission_role` WRITE,`permission` AS p WRITE,`role` AS r WRITE;
INSERT IGNORE INTO `permission_role` (permission_id, roles_id)
SELECT p.id, r.id FROM permission AS p, role AS r WHERE p.permissionName='injMapSysProcOS:display' AND r.roleName='Jedi';
INSERT IGNORE INTO `permission_role` (permission_id, roles_id)
SELECT p.id, r.id FROM permission AS p, role AS r WHERE p.permissionName='injMapSysProcOS:action' AND r.roleName='Jedi';

INSERT IGNORE INTO `permission_role` (permission_id, roles_id)
SELECT p.id, r.id FROM permission AS p, role AS r WHERE p.permissionName='injMapSysProcOS:display' AND r.roleName='sysadmin';
INSERT IGNORE INTO `permission_role` (permission_id, roles_id)
SELECT p.id, r.id FROM permission AS p, role AS r WHERE p.permissionName='injMapSysProcOS:action' AND r.roleName='sysadmin';

INSERT IGNORE INTO `permission_role` (permission_id, roles_id)
SELECT p.id, r.id FROM permission AS p, role AS r WHERE p.permissionName='injMapSysProcOS:display' AND r.roleName='sysreviewer';
UNLOCK TABLES;



--
-- Dumping data for table `role_permission`
--
LOCK TABLES `role_permission` WRITE,`permission` AS p WRITE,`role` AS r WRITE;
INSERT IGNORE INTO `role_permission` (role_id, permissions_id)
SELECT r.id, p.id FROM permission AS p, role AS r WHERE p.permissionName='injMapSysProcOS:display' AND r.roleName='Jedi';
INSERT IGNORE INTO `role_permission` (role_id, permissions_id)
SELECT r.id, p.id FROM permission AS p, role AS r WHERE p.permissionName='injMapSysProcOS:action' AND r.roleName='Jedi';

INSERT IGNORE INTO `role_permission` (role_id, permissions_id)
SELECT r.id, p.id FROM permission AS p, role AS r WHERE p.permissionName='injMapSysProcOS:display' AND r.roleName='sysadmin';
INSERT IGNORE INTO `role_permission` (role_id, permissions_id)
SELECT r.id, p.id FROM permission AS p, role AS r WHERE p.permissionName='injMapSysProcOS:action' AND r.roleName='sysadmin';

INSERT IGNORE INTO `role_permission` (role_id, permissions_id)
SELECT r.id, p.id FROM permission AS p, role AS r WHERE p.permissionName='injMapSysProcOS:display' AND r.roleName='sysreviewer';
UNLOCK TABLES;