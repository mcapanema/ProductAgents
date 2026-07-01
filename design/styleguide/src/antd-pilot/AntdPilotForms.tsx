// design/styleguide/src/antd-pilot/AntdPilotForms.tsx
// AntD Pilot — Buttons & Forms. Compare against Phase 3C (Phase3Forms.tsx).
import { useState } from "react";
import { Button, Checkbox, Form, Input, Radio, Select, Space, Switch } from "antd";
import { Section, Specimen } from "../sg";

export function AntdPilotForms() {
  const [form] = Form.useForm();
  const [submitted, setSubmitted] = useState<Record<string, unknown> | null>(null);

  return (
    <Section
      id="antd-forms"
      title="AntD Pilot · Buttons & Forms"
      desc="Ant Design's Button/Input/Select/Checkbox/Radio/Switch/Form, themed via ConfigProvider from the Instrument tokens — compare against Phase 3C."
    >
      <Specimen label="Button variants">
        <Space wrap>
          <Button type="primary">Primary</Button>
          <Button>Default</Button>
          <Button type="dashed">Dashed</Button>
          <Button type="text">Text</Button>
          <Button type="link">Link</Button>
          <Button type="primary" danger>Danger</Button>
          <Button type="primary" loading>Loading</Button>
          <Button type="primary" disabled>Disabled</Button>
        </Space>
      </Specimen>

      <Specimen label="Button sizes">
        <Space wrap align="center">
          <Button type="primary" size="small">Small</Button>
          <Button type="primary" size="middle">Middle</Button>
          <Button type="primary" size="large">Large</Button>
        </Space>
      </Specimen>

      <Specimen label="Form (validated)">
        <Form
          form={form}
          layout="vertical"
          style={{ maxWidth: "var(--width-dialog-sm)" }}
          onFinish={(values) => setSubmitted(values)}
        >
          <Form.Item
            label="Workspace name"
            name="workspace"
            rules={[{ required: true, message: "Workspace name is required" }]}
          >
            <Input placeholder="e.g. default" />
          </Form.Item>
          <Form.Item label="Default model provider" name="provider" initialValue="anthropic">
            <Select
              options={[
                { value: "anthropic", label: "Anthropic" },
                { value: "openai", label: "OpenAI" },
                { value: "openrouter", label: "OpenRouter" },
              ]}
            />
          </Form.Item>
          <Form.Item name="riskGate" valuePropName="checked" initialValue={true}>
            <Checkbox>Require human approval before governance</Checkbox>
          </Form.Item>
          <Form.Item label="Density" name="density" initialValue="comfortable">
            <Radio.Group
              optionType="button"
              options={[
                { value: "comfortable", label: "Comfortable" },
                { value: "compact", label: "Compact" },
              ]}
            />
          </Form.Item>
          <Form.Item label="Enable connector sync" name="syncEnabled" valuePropName="checked" initialValue={false}>
            <Switch />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">Save settings</Button>
          </Form.Item>
        </Form>
        {submitted && (
          <pre className="sg-desc" aria-live="polite">{JSON.stringify(submitted, null, 2)}</pre>
        )}
      </Specimen>
    </Section>
  );
}
